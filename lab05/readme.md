# Лабораторная работа №5. Ansible playbook для настройки тестового сервера

## Цель работы

Научиться создавать Ansible-плейбуки для автоматизации настройки серверов.

## Задание

1. Создать в репозитории каталог `lab05` и скопировать в него файлы работы lab04.
2. Создать файл `compose.yaml` с сервисом контроллера Jenkins `jenkins-controller` и установить плагины Docker, Docker Pipeline, GitHub Integration и SSH Agent.
3. Написать `Dockerfile.ssh_agent` для SSH-агента с PHP, создать для него SSH-ключи, настроить Jenkins на эти ключи и добавить сервис `ssh-agent`.
4. Написать `Dockerfile.ansible_agent` для агента Ansible на основе Ubuntu, создать SSH-ключи для связи Jenkins с этим агентом и отдельные ключи для связи агента с тестовым сервером (вход под пользователем `ansible`), добавить сервис `ansible-agent`.
5. Написать `Dockerfile.test_server` для тестового сервера на основе Ubuntu с openssh-server, создать на нём пользователя `ansible` и настроить вход по ключу.
6. Создать каталог `ansible` с инвентарём `hosts.ini` и плейбуком `setup_test_server.yml`, который устанавливает и настраивает Apache2, PHP с расширениями и виртуальный хост для PHP-проекта.
7. Создать каталог `pipelines` и в нём три конвейера Jenkins:
   - `php_build_and_test_pipeline.groovy`: клонирование, установка зависимостей Composer, запуск PHPUnit, отчёт о тестах;
   - `ansible_setup_pipeline.groovy`: клонирование, выполнение плейбука настройки тестового сервера;
   - `php_deploy_pipeline.groovy`: клонирование, копирование файлов проекта на тестовый сервер, настройка проекта на сервере.
8. Открыть адрес тестового сервера в браузере и убедиться, что PHP-проект развёрнут и работает.
9. Оформить отчёт `readme.md` и ответить на контрольные вопросы.

## Используемые технологии

| Компонент | Версия | Где используется |
|---|---|---|
| Jenkins | 2.580.1 LTS (образ `jenkins/jenkins:lts`, Java 21) | контроллер `jenkins-controller` |
| Ubuntu | 24.04.5 LTS | управляющий узел Ansible `ansible-agent` |
| Ubuntu | 22.04.5 LTS | тестовый сервер `test-server` |
| ansible-core | 2.20.10 | управляющий узел, виртуальное окружение `/opt/ansible` |
| Python | 3.12.3 | интерпретатор виртуального окружения Ansible |
| Jinja2 | 3.1.6 | шаблоны `gradebook.conf.j2` и `config.php.j2` |
| OpenJDK | 21.0.12 (`openjdk-21-jre-headless`) | процесс `remoting.jar` на управляющем узле |
| OpenSSH | 9.6p1 на управляющем узле, 8.9p1 на сервере | подключения Jenkins и Ansible |
| Apache | 2.4.52 | веб-сервер на тестовом сервере |
| PHP | 8.1.2 (`libapache2-mod-php`, `php-mbstring`, `php-intl`, ICU 70.1) | выполнение `gradebook` на тестовом сервере |
| PHP | 8.4.27 | SSH-агент `ssh-agent` (сборка и тесты) |
| Composer | 2.10.3 | установка PHPUnit на SSH-агенте |
| PHPUnit | 10.5.66 | модульные тесты |

Плагины Jenkins:

| Плагин | Версия | Зачем |
|---|---|---|
| Docker (`docker-plugin`) | 1336.v3711dec712de | требуется заданием: запуск агентов в контейнерах Docker |
| Docker Pipeline (`docker-workflow`) | 653.v2f2c08eff0ec | требуется заданием: шаги `docker` в конвейерах |
| GitHub Integration (`github-pullrequest`) | 0.7.5 | требуется заданием: запуск конвейера при push и pull request в GitHub |
| SSH Agent (`ssh-agent`) | 433.v9e73d67c3f74 | требуется заданием: шаг `sshagent`, которым Ansible получает ключ от тестового сервера |
| SSH Build Agents (`ssh-slaves`) | 3.1097.v868116049892 | подключение узлов `ssh-agent1` и `ansible-control-node` по SSH |
| Git | 5.11.0 | получение конвейеров и кода из репозитория |
| Pipeline (`workflow-aggregator`) | 608.v67378e9d3db_1 | декларативные конвейеры |
| JUnit | 1442.vb_b_a_467df2767 | шаг `junit`, результаты тестов на странице сборки |

Плагины Docker, Docker Pipeline и GitHub Integration установлены по заданию. В моих конвейерах они не используются: агенты подключаются по SSH, а сборки я запускаю вручную.

## Описание проекта

### Стенд

В `compose.yaml` описаны четыре сервиса, и Compose подключает их к общей сети `jenkins-network`. Ниже перечислено, кто к кому подключается и каким ключом подтверждает, что это именно он:

1. **Контроллер Jenkins** (`jenkins-controller`) подключается по SSH к SSH-агенту (`ssh-agent`) под пользователем `jenkins`. Закрытый ключ пары `jenkins_agent_ssh_key` хранится в учётных данных Jenkins, открытый ключ агент получает из переменной `JENKINS_AGENT_SSH_PUBKEY` (файл `.env`), как в lab04. На этом агенте собирается проект и выполняются тесты.
2. **Контроллер Jenkins** подключается по SSH к управляющему узлу Ansible (`ansible-agent`) под пользователем `jenkins`. Для этого используется отдельная пара `ansible_agent_ssh_key`: её открытый ключ копируется в образ при сборке. С этого узла запускаются плейбуки.
3. **Управляющий узел Ansible** подключается по SSH к тестовому серверу (`test-server`) под пользователем `ansible`. Используется третья пара `test_server_ansible_key`: открытый ключ копируется в образ сервера, закрытый Jenkins отдаёт управляющему узлу лишь пока выполняется блок `sshagent`, а после блока его там уже нет.
4. **Браузер** на моём компьютере открывает тестовый сервер по адресу `http://localhost:8082/`: порт 80 контейнера опубликован на хосте как 8082.

Управляющий узел (control node) в терминологии Ansible: машина, на которой установлен Ansible и с которой запускаются плейбуки. Серверы, которые он настраивает, называются управляемыми узлами (managed nodes). На управляемых узлах Ansible ничего не устанавливает заранее: ему нужны только SSH и Python.

Три пары ключей разделены намеренно. Каждая пара открывает ровно одну дверь: ключ SSH-агента не подходит к управляющему узлу, а ключ управляющего узла не подходит к тестовому серверу. Если один ключ окажется скомпрометирован, остальные связи останутся защищены, а заменить нужно будет только одну пару.

### Проект gradebook

Проект `gradebook` перенесён из lab04: это электронный журнал оценок студента по 10-балльной шкале, принятой в Молдове. Класс `GradeBook` хранит оценки по предметам, считает средний балл по предмету и общий средний балл, а предметы со средним баллом ниже 5 возвращает как задолженности. Код находится в пространстве имён `Bordeniuc\Gradebook`, тесты написаны на PHPUnit 10.5 с атрибутами `#[TestDox]`.

Для этой работы проект нужно было выложить на веб-сервер, поэтому я добавил к нему три файла:

- `src/GradeTextParser.php`: класс, который превращает текст вида `Математика: 8 9 10` (одна строка на предмет) в объект `GradeBook`. Строка без двоеточия, строка без оценок и нечисловая оценка вызывают `GradeException` с номером строки, а оценки вне шкалы отклоняет сам журнал;
- `tests/GradeTextParserTest.php`: три теста для разбора текста;
- `public/index.php`: веб-страница с формой. В поле вводятся оценки, после отправки формы страница показывает таблицу `Предмет | Оценки | Средний балл | Итог`, отмечает несданные предметы и выводит общий средний балл.

В класс `GradeBook` добавлен метод `gradesFor()`, который возвращает оценки по предмету: он нужен странице для столбца «Оценки». Всего в проекте теперь 12 тестов.

## Описание файлов

Итоговая структура каталога:

```
lab05/
├── compose.yaml                      четыре сервиса стенда
├── Dockerfile.ssh_agent              SSH-агент с PHP (Dockerfile из lab04)
├── Dockerfile.ansible_agent          управляющий узел Ansible
├── Dockerfile.test_server            тестовый сервер
├── secrets/
│   ├── jenkins_agent_ssh_key.pub     Jenkins -> ssh-agent
│   ├── ansible_agent_ssh_key.pub     Jenkins -> ansible-agent
│   └── test_server_ansible_key.pub   ansible-agent -> test-server
├── ansible/
│   ├── hosts.ini                     инвентарь
│   ├── setup_test_server.yml         настройка сервера
│   ├── deploy_gradebook.yml          копирование файлов проекта
│   ├── configure_gradebook.yml       настройка проекта на сервере
│   └── templates/
│       ├── gradebook.conf.j2         виртуальный хост Apache
│       └── config.php.j2             настройки страницы
├── pipelines/
│   ├── php_build_and_test_pipeline.groovy
│   ├── ansible_setup_pipeline.groovy
│   └── php_deploy_pipeline.groovy
├── gradebook/                        PHP-проект
│   ├── composer.json, composer.lock, phpunit.xml
│   ├── src/GradeBook.php, src/GradeException.php, src/GradeTextParser.php
│   ├── tests/GradeBookTest.php, tests/GradeTextParserTest.php
│   └── public/index.php
└── readme.md
```

Файлы lab04 скопированы в начале работы, затем `Dockerfile` переименован в `Dockerfile.ssh_agent`, а `docker-compose.yml` в `compose.yaml`, как требует задание. `Jenkinsfile` из lab04 удалён: его роль теперь выполняет `pipelines/php_build_and_test_pipeline.groovy`. Закрытые ключи и `.env` хранятся только локально. Во всех Dockerfile, плейбуках, шаблонах и конвейерах перед каждым блоком стоит комментарий на русском языке, который объясняет не только что делается, но и почему.

### compose.yaml

Сервисы `jenkins-controller` и `ssh-agent` перенесены из lab04 без изменений, кроме имени Dockerfile. Добавлены два сервиса:

```yaml
  ansible-agent:
    build:
      context: .
      dockerfile: Dockerfile.ansible_agent
    container_name: ansible-agent
    depends_on:
      - jenkins-controller
      - test-server
    networks:
      - jenkins-network

  test-server:
    build:
      context: .
      dockerfile: Dockerfile.test_server
    container_name: test-server
    ports:
      - "8082:80"
    networks:
      - jenkins-network
```

- `ansible-agent` не получает переменных окружения: открытый ключ Jenkins уже скопирован в образ;
- у `ansible-agent` нет тома для рабочего каталога. Каждая сборка начинается с клонирования репозитория, а архив и `known_hosts` создаются заново, поэтому хранить их между пересозданиями контейнера не нужно;
- `depends_on` запускает управляющий узел после контроллера и тестового сервера. Это важно для команды `docker compose up -d ansible-agent`: Compose поднимет и обе зависимости;
- порт 80 тестового сервера опубликован как `8082`, потому что `8080` занят веб-интерфейсом Jenkins;
- тома `jenkins_home`, `jenkins_agent_volume` и сеть `jenkins-network` остались как в lab04. Внутри сети контейнеры находят друг друга по именам сервисов, поэтому в инвентаре Ansible записано просто `test-server`.

### Dockerfile.ssh_agent

Это `Dockerfile` из lab04: образ `jenkins/ssh-agent:jdk21`, к которому добавлены `php-cli`, `php-xml`, `php-mbstring`, `unzip` и Composer 2.10.3. Я изменил только оформление комментариев. Подробно этот файл описан в отчёте lab04.

### Dockerfile.ansible_agent

```dockerfile
FROM ubuntu:24.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        openssh-server openssh-client git python3 python3-venv openjdk-21-jre-headless \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/ansible \
    && /opt/ansible/bin/pip install --no-cache-dir "ansible-core==2.20.*"

ENV PATH="/opt/ansible/bin:${PATH}"

RUN ln -s /opt/ansible/bin/ansible /opt/ansible/bin/ansible-playbook /opt/ansible/bin/ansible-galaxy /usr/local/bin/

RUN adduser --disabled-password --gecos "" jenkins \
    && mkdir -p /home/jenkins/.ssh /home/jenkins/agent /run/sshd

COPY secrets/ansible_agent_ssh_key.pub /home/jenkins/.ssh/authorized_keys
...
RUN echo "PasswordAuthentication no" >> /etc/ssh/sshd_config \
    && echo "PermitRootLogin no" >> /etc/ssh/sshd_config

CMD ["/usr/sbin/sshd", "-D"]
```

Почему образ устроен именно так:

- **Ubuntu 24.04.** Задание требует Ubuntu. 24.04 является текущим LTS-выпуском, в нём есть Python 3.12 и пакет `openjdk-21-jre-headless`.
- **Java 21.** Узел подключается к Jenkins как обычный SSH-агент: плагин SSH Build Agents копирует на него `remoting.jar` и запускает его командой `java`. Контроллер Jenkins 2.580.1 работает на Java 21, и агент должен иметь не ниже этой версии (в lab04 я уже столкнулся с ошибкой `UnsupportedClassVersionError` на Java 17).
- **Ansible в виртуальном окружении.** В Ubuntu 24.04 команда `pip install` вне виртуального окружения отказывается работать с ошибкой `externally-managed-environment`: это правило PEP 668, которое защищает системные пакеты Python от изменений через pip. Поэтому Ansible ставится в отдельное окружение `/opt/ansible`. Пакет `ansible` из apt я не взял: он старее и тянет полный набор коллекций, из которых в этой работе не нужна ни одна. Пакет `ansible-core` содержит только встроенные модули `ansible.builtin` (apt, service, template, file, lineinfile, unarchive, uri и другие), и их хватает для всех трёх плейбуков. Версия ограничена веткой 2.20, чтобы пересборка образа не принесла несовместимых изменений.
- **Ссылки в /usr/local/bin.** `ENV PATH` действует для процессов, которые запускает Docker, но не для SSH-сессий. Подробности в проблеме 1.
- **/run/sshd.** Это каталог разделения привилегий (privilege separation directory): в нём sshd запускает непривилегированный процесс, который обрабатывает данные от клиента до входа пользователя. В системе с systemd этот каталог создаётся при запуске службы, а в контейнере его нет, и `sshd -D` сразу завершается с сообщением `Missing privilege separation directory: /run/sshd`.
- **Строки в конце sshd_config.** В `sshd_config` для каждого параметра действует первое найденное значение. В образе `PasswordAuthentication` и `PermitRootLogin` закомментированы, а каталог `sshd_config.d/` пуст, поэтому строки, дописанные в конец файла, оказываются первыми значениями и действуют.

### Dockerfile.test_server

```dockerfile
FROM ubuntu:22.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-server sudo python3 \
    && rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password --gecos "" ansible \
    && echo "ansible ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ansible \
    && chmod 440 /etc/sudoers.d/ansible \
    && mkdir -p /home/ansible/.ssh /run/sshd

COPY secrets/test_server_ansible_key.pub /home/ansible/.ssh/authorized_keys
...
EXPOSE 22 80
CMD ["/usr/sbin/sshd", "-D"]
```

- **Ubuntu 22.04.** Я выбрал предыдущий LTS-выпуск, потому что на серверах часто работает не самая новая система. В его репозитории PHP 8.1, а `gradebook` требует `"php": ">=8.1"`, поэтому новый код страницы написан без синтаксиса PHP 8.2 и новее.
- **Только openssh-server, sudo и python3.** Это всё, что нужно Ansible: вход по SSH, повышение прав и интерпретатор для модулей. Пакетов веб-сервера в образе нет вообще: пока не выполнен `setup_test_server.yml`, порт 80 никто не слушает, и по этому легко убедиться, что сервер настроил именно Ansible.
- **Пользователь ansible.** Ключ `--disabled-password` команды `adduser` оставляет учётную запись без пароля, поэтому единственный способ войти: ключ из `authorized_keys`. Файл `/etc/sudoers.d/ansible` разрешает ему `sudo` без пароля: задачи с `become: true` выполняются через `sudo`, и без этой строки Ansible ждал бы ввода пароля. Права `440` обязательны, файл с другими правами `sudo` пропускает.
- `/run/sshd` и строки `sshd_config` работают так же, как в образе управляющего узла.

### Открытые ключи в репозитории

В `secrets/` закоммичены только три файла `.pub`. Открытый ключ не является секретом: по нему нельзя восстановить закрытый ключ, и он только сообщает серверу, какой ключ пускать. Поэтому образы, в которые эти ключи копируются, можно публиковать. Закрытые ключи перечислены в корневом `.gitignore`:

```
# lab05: private SSH keys (public keys are committed)
lab05/secrets/jenkins_agent_ssh_key
lab05/secrets/ansible_agent_ssh_key
lab05/secrets/test_server_ansible_key
```

Там же исключены `vendor/`, кеш PHPUnit, каталог отчётов `build/` и архив `gradebook.tar.gz`, который создаёт конвейер выкладки. Если ключ понадобится заменить, нужно создать новую пару, пересобрать образ и обновить учётные данные в Jenkins.

### Три значения слов «SSH Agent»

В работе одно название встречается в трёх разных смыслах, и их легко перепутать:

1. **Плагин Jenkins SSH Agent** (`ssh-agent`): даёт шаг конвейера `sshagent(credentials: [...]) { ... }`. Его требует задание, и именно им Jenkins передаёт Ansible ключ от тестового сервера.
2. **Контейнер `ssh-agent`** из lab04: агент Jenkins с PHP, к которому контроллер подключается по SSH. Подключение выполняет другой плагин, SSH Build Agents.
3. **Программа `ssh-agent`** из пакета OpenSSH: хранит закрытые ключи в памяти и отдаёт их клиенту `ssh` через сокет `SSH_AUTH_SOCK`. Шаг `sshagent` запускает именно эту программу на управляющем узле, поэтому в образ установлен `openssh-client`.

### ansible/hosts.ini

```ini
[webservers]
test-server

[webservers:vars]
ansible_user=ansible
ansible_python_interpreter=/usr/bin/python3
```

- группа `webservers` содержит один сервер. `test-server` здесь не адрес, а имя сервиса из `compose.yaml`: его IP внутри `jenkins-network` сообщает встроенный DNS Docker, и `ansible_host` указывать не приходится;
- `ansible_user=ansible`: вход под пользователем `ansible`, как требует задание;
- `ansible_python_interpreter` задан явно: на Ubuntu 22.04 это `/usr/bin/python3` версии 3.10, и мне удобнее видеть путь в инвентаре, чем полагаться на автоматический выбор;
- путь к закрытому ключу в инвентаре не указан. Ключ приходит из программы `ssh-agent`, которую запускает шаг `sshagent` в конвейере. Файла `ansible.cfg` нет: всё, что нужно для подключения, записано в инвентаре, а команды запускаются как `ansible-playbook -i hosts.ini ...` из каталога `lab05/ansible`.

### Проверка ключа хоста тестового сервера

SSH-клиент при первом подключении проверяет ключ хоста, а Ansible по умолчанию эту проверку не отключает. Я рассматривал три варианта:

1. **Отключить проверку** (`host_key_checking = False` в `ansible.cfg`). Проще всего, но тогда отпечаток ключа, который прислал сервер, вообще ни с чем не сверяется, и проверка теряет смысл.
2. **Сканировать ключ перед каждым запуском** командой `ssh-keyscan` и записывать его в `known_hosts`. Проверка в Ansible остаётся включённой, а ключ всегда актуален, даже если контейнер сервера пересоздан.
3. **Заранее записать ключ в файл** `known_hosts` и хранить его в репозитории. Самый строгий вариант, но после каждой пересборки образа сервера файл нужно обновлять вручную.

Я выбрал второй вариант. Сканирование выполняется внутри изолированной сети `jenkins-network`, к которой нет доступа снаружи, поэтому риск подмены хоста в момент сканирования низкий, а сам Ansible ни разу не работает с отключённой проверкой.

### Плейбуки и шаблоны

`setup_test_server.yml` подробно разобран в разделе «Описание плейбука setup_test_server.yml». Два других плейбука и шаблоны описаны там же.

### Конвейеры

Все три конвейера подключаются в Jenkins как «Pipeline script from SCM» из репозитория `https://github.com/srulimoisovich/automation.git`, ветка `*/main`. Названия этапов на русском языке, перед каждым блоком стоит комментарий.

Первый этап у всех трёх одинаковый:

```groovy
stage('Клонирование репозитория') {
    steps {
        checkout scm
        sh 'git log -1 --format="%h %an %s"'
    }
}
```

Декларативный конвейер сам получает репозиторий перед первым этапом, но задание перечисляет клонирование как отдельный этап, поэтому `checkout scm` повторён явно. Шаг `checkout scm` берёт адрес и ветку из настроек задания, так что в файле конвейера адрес репозитория не дублируется. `git log -1` печатает в журнал сборки коммит, который был собран.

**php_build_and_test_pipeline.groovy** выполняется на узле с меткой `php-agent` (SSH-агент из lab04):

```groovy
stage('Запуск тестов') {
    steps {
        sh '''
            cd lab05/gradebook
            vendor/bin/phpunit --testdox --log-junit build/junit.xml --testdox-html build/testdox.html
        '''
    }
}

stage('Отчёт о тестах') {
    steps {
        junit 'lab05/gradebook/build/junit.xml'
        archiveArtifacts artifacts: 'lab05/gradebook/build/testdox.html'
    }
}
```

Этап «Установка зависимостей» выполняет `composer install --no-interaction --optimize-autoloader`. PHPUnit пишет два отчёта: JUnit XML, который шаг `junit` превращает в результаты тестов на странице сборки, и HTML-список тестов, который сохраняется как артефакт. Плагина HTML Publisher в Jenkins нет, поэтому HTML-отчёт просто архивируется и открывается из списка артефактов.

**ansible_setup_pipeline.groovy** выполняется на узле с меткой `ansible-control`:

```groovy
stage('Настройка тестового сервера') {
    steps {
        sshagent(credentials: ['test_server_ansible_key']) {
            sh '''
                cd lab05/ansible
                mkdir -p ~/.ssh
                ssh-keyscan -t ed25519 test-server > ~/.ssh/known_hosts
                ansible --version
                ansible-playbook -i hosts.ini setup_test_server.yml
            '''
        }
    }
}
```

Шаг `sshagent` запускает программу `ssh-agent`, добавляет в неё закрытый ключ из учётных данных `test_server_ansible_key` и экспортирует `SSH_AUTH_SOCK`. Ansible вызывает обычный `ssh`, а тот берёт ключ из агента. Ключ находится только в памяти и только на время блока: после него Jenkins останавливает `ssh-agent`, и на диске управляющего узла ключа нет.

**php_deploy_pipeline.groovy** тоже выполняется на узле `ansible-control` и состоит из трёх этапов:

- «Клонирование репозитория»;
- «Копирование файлов на сервер»: `tar -czf lab05/gradebook.tar.gz -C lab05/gradebook src public` собирает архив только из `src/` и `public/` (тесты, `phpunit.xml` и Composer на сервере не нужны), затем внутри `sshagent` выполняются `ssh-keyscan` и `ansible-playbook -i hosts.ini deploy_gradebook.yml`;
- «Настройка проекта на сервере»: `ansible-playbook -i hosts.ini configure_gradebook.yml -e build_number=$BUILD_NUMBER`. Строка Groovy взята в одинарные кавычки, поэтому `$BUILD_NUMBER` подставляет оболочка из переменной окружения сборки.

### public/index.php

На сервер не попадают ни Composer, ни `vendor/`, поэтому автозагрузчик Composer там отсутствует. У библиотеки нет внешних зависимостей во время работы, и вместо Composer страница регистрирует короткий собственный автозагрузчик:

```php
spl_autoload_register(static function (string $className): void {
    $prefix = 'Bordeniuc\\Gradebook\\';
    if (!str_starts_with($className, $prefix)) {
        return;
    }
    $relativeName = substr($className, strlen($prefix));
    require __DIR__ . '/../src/' . str_replace('\\', '/', $relativeName) . '.php';
});
```

Он делает то же, что правило PSR-4 в `composer.json`: класс `Bordeniuc\Gradebook\GradeBook` ищется в файле `../src/GradeBook.php`.

Остальная часть страницы:

- подключает `../config.php`, если он есть (его создаёт Ansible), иначе берёт значения по умолчанию;
- показывает форму с полем `grades`, в котором заранее стоит пример;
- после отправки формы разбирает текст через `GradeTextParser` и строит таблицу. Строки несданных предметов (средний балл ниже `GradeBook::PASSING_AVERAGE`) получают светло-красный фон и отметку «не сдан»;
- подпись таблицы (`<caption>`) берёт границы шкалы и проходной балл из констант класса;
- средние баллы печатает `NumberFormatter` с локалью `ro_MD` и двумя знаками после запятой, поэтому 8.67 выглядит как `8,67`;
- сообщение `GradeException` показывает над формой;
- внизу печатает номер сборки, время выкладки и имя сервера из `config.php`. Время хранится в UTC и переводится в часовой пояс из `php.ini`.

Оформление простое: встроенный блок `<style>` с шрифтом с засечками и шириной страницы до 720px. У таблицы нет вертикальных рамок: строки разделены тонкими серыми линиями, а над шапкой проходит линия потолще. JavaScript и сторонние библиотеки не используются.

## Ход работы

### 1. Создание SSH-ключей

Для работы нужны три пары ключей. Все они созданы в каталоге `lab05/secrets` командой `ssh-keygen` с типом ed25519, пустой парольной фразой (иначе Jenkins и Ansible не смогли бы использовать ключ без участия человека) и комментарием, по которому видно назначение ключа:

```bash
cd lab05/secrets
ssh-keygen -t ed25519 -N '' -f jenkins_agent_ssh_key -C 'jenkins-to-ssh-agent-lab05'
ssh-keygen -t ed25519 -N '' -f ansible_agent_ssh_key -C 'jenkins-to-ansible-agent-lab05'
ssh-keygen -t ed25519 -N '' -f test_server_ansible_key -C 'ansible-to-test-server-lab05'
```

| Пара | Кто подключается | К кому | Где открытый ключ | Где закрытый ключ |
|---|---|---|---|---|
| `jenkins_agent_ssh_key` | Jenkins | `ssh-agent`, пользователь `jenkins` | `.env` -> переменная `JENKINS_AGENT_SSH_PUBKEY` | учётные данные Jenkins |
| `ansible_agent_ssh_key` | Jenkins | `ansible-agent`, пользователь `jenkins` | копируется в образ (`COPY`) | учётные данные Jenkins |
| `test_server_ansible_key` | Ansible на `ansible-agent` | `test-server`, пользователь `ansible` | копируется в образ (`COPY`) | учётные данные Jenkins, на агент попадает через `sshagent` |

Пара для SSH-агента создана заново, ключи lab04 в lab05 не используются. Файлы `.pub` закоммичены, закрытые ключи перечислены в `.gitignore` (почему так можно, сказано в разделе «Открытые ключи в репозитории»).

### 2. Файл .env

Как и в lab04, SSH-агент получает открытый ключ из переменной окружения, которую Compose читает из файла `.env` рядом с `compose.yaml`:

```bash
echo "JENKINS_AGENT_SSH_PUBKEY=$(cat secrets/jenkins_agent_ssh_key.pub)" > .env
```

Файл `.env` в репозиторий не попадает: его исключает правило `.env` в корневом `.gitignore`.

### 3. Сборка и запуск стенда

Сначала я собрал и запустил только новые сервисы, чтобы проверить их отдельно:

```bash
docker compose up -d --build ansible-agent test-server
```

Compose собрал два образа: `Dockerfile.ansible_agent` (Ubuntu 24.04, Java 21, git, sshd, ansible-core в виртуальном окружении, пользователь `jenkins` с открытым ключом Jenkins) и `Dockerfile.test_server` (Ubuntu 22.04, sshd, sudo, python3, пользователь `ansible` с открытым ключом Ansible); подробно они разобраны в разделе «Описание файлов». Кроме двух названных сервисов, запустился и `jenkins-controller`: он указан в `depends_on` у `ansible-agent`, и Compose всегда поднимает зависимости вместе с сервисом. Не запустился только `ssh-agent`, от которого никто из названных сервисов не зависит.

```
$ docker compose ps --format 'table {{.Service}}\t{{.State}}'
SERVICE              STATE
ansible-agent        running
jenkins-controller   running
test-server          running
```

Проверка пользователя `ansible` и его прав на сервере:

```
$ docker compose exec test-server id ansible
uid=1000(ansible) gid=1000(ansible) groups=1000(ansible)
$ docker compose exec test-server sudo -l -U ansible
Matching Defaults entries for ansible on 89339eefeda2:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin\:/snap/bin, use_pty

User ansible may run the following commands on 89339eefeda2:
    (ALL) NOPASSWD: ALL
```

Проверка, что sshd на сервере работает и виден с управляющего узла по имени сервиса:

```
$ docker compose exec ansible-agent ssh-keyscan -t ed25519 test-server
# test-server:22 SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.18
test-server ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINLwNKqesOnlk5zdjq3hcV+0pgSUj8Imh3L+v/ouPiHD
```

Первая строка, комментарий с версией сервера, напечатана в поток ошибок, а вторая строка, сам ключ, в стандартный вывод. Поэтому при перенаправлении `> ~/.ssh/known_hosts` в файл попадает только ключ, а комментарий остаётся в журнале сборки.

Версия Ansible в образе:

```
$ docker compose exec ansible-agent ansible --version
ansible [core 2.20.10]
  config file = None
  configured module search path = ['/root/.ansible/plugins/modules', '/usr/share/ansible/plugins/modules']
```

После этого я запустил весь стенд, и Compose собрал образ SSH-агента и запустил последний контейнер:

```bash
docker compose up -d --build
```

### 4. Настройка Jenkins Controller

1. Открыл `http://localhost:8080`, взял пароль первого входа командой `docker compose exec jenkins-controller cat /var/jenkins_home/secrets/initialAdminPassword` и ввёл его на странице «Unlock Jenkins».
2. Выбрал «Install suggested plugins». В этот набор входят Pipeline, Git, SSH Build Agents, JUnit, Credentials Binding и другие.
3. Создал пользователя-администратора и оставил адрес Jenkins по умолчанию.
4. В Manage Jenkins -> Plugins -> Available plugins нашёл и установил четыре плагина, которые требует задание: **Docker**, **Docker Pipeline**, **GitHub Integration** и **SSH Agent**. После установки перезапустил Jenkins (флажок «Restart Jenkins when installation is complete»).
5. Проверил в Installed plugins, что все плагины включены; их версии приведены в таблице раздела «Используемые технологии».

### 5. Учётные данные

В Manage Jenkins -> Credentials -> System -> Global credentials -> Add Credentials добавлены три записи вида «SSH Username with private key». Закрытый ключ вставлялся в поле «Private Key» через «Enter directly», парольная фраза пустая.

| ID | Username | Закрытый ключ | Описание |
|---|---|---|---|
| `jenkins_agent_ssh_key` | `jenkins` | `secrets/jenkins_agent_ssh_key` | Ключ Jenkins для SSH-агента с PHP |
| `ansible_agent_ssh_key` | `jenkins` | `secrets/ansible_agent_ssh_key` | Ключ Jenkins для управляющего узла Ansible |
| `test_server_ansible_key` | `ansible` | `secrets/test_server_ansible_key` | Ключ Ansible для тестового сервера |

Поле Username у третьей записи равно `ansible`. Шаг `sshagent` использует только сам ключ, а пользователь для входа на сервер берётся из `ansible_user` в инвентаре, но совпадающее имя делает запись понятной.

### 6. Узел ssh-agent1

Узел создан так же, как в lab04 (Manage Jenkins -> Nodes -> New Node, Permanent Agent):

- Name: `ssh-agent1`, Labels: `php-agent`, Number of executors: `2`;
- Remote root directory: `/home/jenkins/agent`;
- Launch method: «Launch agents via SSH», Host: `ssh-agent`, Credentials: `jenkins_agent_ssh_key`;
- Host Key Verification Strategy: «Manually provided key Verification Strategy», ключ из `docker compose exec ssh-agent cat /etc/ssh/ssh_host_ed25519_key.pub`.

### 7. Узел ansible-control-node

Второй постоянный узел для управляющего узла Ansible:

- Name: `ansible-control-node`, Description: «Управляющий узел Ansible»;
- Number of executors: `1`, Labels: `ansible-control`;
- Remote root directory: `/home/jenkins/agent` (каталог создан в Dockerfile и принадлежит `jenkins`);
- Launch method: «Launch agents via SSH», Host: `ansible-agent`, Credentials: `ansible_agent_ssh_key`;
- Host Key Verification Strategy: «Manually provided key Verification Strategy». Ключ хоста я взял командой:

```
$ docker compose exec ansible-agent cat /etc/ssh/ssh_host_ed25519_key.pub
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFl4MYbrRvlBmljyLn8rWNeLCxGSR/EiWagk/yZrcqEA root@buildkitsandbox
```

и вставил в поле первые две части строки (тип и ключ). Журнал подключения узла (Nodes -> ansible-control-node -> Log), время в начале строк убрано:

```
[SSH] Opening SSH connection to ansible-agent:22.
[SSH] SSH host key matched the key required for this connection. Connection will be allowed.
[SSH] Authentication successful.
[SSH] The remote user's environment is:
...
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin
...
[SSH] Starting agent process: cd "/home/jenkins/agent" && java  -jar remoting.jar -workDir /home/jenkins/agent -jar-cache /home/jenkins/agent/remoting/jarCache
...
Agent successfully connected and online
```

В строке `PATH` нет каталога `/opt/ansible/bin`, хотя он добавлен в `ENV PATH` в Dockerfile. Сразу я этого не заметил, и это стало проблемой 1.

### 8. Задания Jenkins

Три задания вида Pipeline (New Item -> Pipeline). У всех трёх в разделе Pipeline выбрано «Pipeline script from SCM»:

- SCM: Git, Repository URL: `https://github.com/srulimoisovich/automation.git`, учётные данные не нужны (репозиторий открытый);
- Branch Specifier: `*/main`;
- Script Path: по таблице ниже, флажок Lightweight checkout включён.

| Задание | Script Path |
|---|---|
| `lab05-gradebook-build` | `lab05/pipelines/php_build_and_test_pipeline.groovy` |
| `lab05-test-server-setup` | `lab05/pipelines/ansible_setup_pipeline.groovy` |
| `lab05-gradebook-deploy` | `lab05/pipelines/php_deploy_pipeline.groovy` |

### 9. Сборка и тесты

Задание `lab05-gradebook-build` прошло успешно с первого запуска (сборка №1): Composer установил 26 пакетов, все 12 тестов прошли. Полный вывод приведён для сборки №2 в разделе «Результаты».

### 10. Настройка тестового сервера

Первый запуск `lab05-test-server-setup` (сборка №1) завершился ошибкой `ansible: not found` (проблема 1). После исправления Dockerfile и пересборки управляющего узла сборка №2 настроила сервер. Сборки №3 и №5 были повторными запусками на уже настроенном сервере, и в них все задачи получили статус `ok`.

После комментариев к файлам (коммит `eda70b2`) я пересоздал контейнер тестового сервера, чтобы проверить настройку с нуля на итоговой версии файлов, и запустил настройку ещё раз: это сборка №4, её вывод приведён в разделе «Результаты».

### 11. Выкладка проекта

Задание `lab05-gradebook-deploy` в первой сборке выложило проект, но Ansible вывел предупреждение об устаревшем способе обращения к фактам (проблема 2). Итоговая сборка выкладки на чистый сервер: №4.

### 12. Проверка в браузере

В браузере я открыл `http://localhost:8082/`, увидел форму с примером оценок, нажал «Посчитать средние баллы» и получил таблицу, в которой физика со средним баллом 4,00 отмечена как несданная. Те же проверки из командной строки:

```
$ curl -s http://localhost:8082/ | grep -o 'Сборка №[0-9]*'
Сборка №4
$ curl -s --data-urlencode $'grades=Математика: 8 9 10\nФизика: 4 5 3' http://localhost:8082/ | grep -E '<td>|class="failed"'
                <td>Математика</td>
                <td>8, 9, 10</td>
                <td>9,00</td>
                <td>сдан</td>
                                <tr class="failed">
                <td>Физика</td>
                <td>4, 5, 3</td>
                <td>4,00</td>
                <td>не сдан</td>
```

Номер на странице совпадает с номером сборки выкладки, а средний балл напечатан с десятичной запятой, значит работают и `config.php`, и расширение intl. Ошибки ввода тоже обрабатываются:

```
$ curl -s --data-urlencode $'grades=Математика: 8 9 10\nФизика 7' http://localhost:8082/ | grep 'class="error"'
    <p class="error">Ошибка: Строка 2: нет двоеточия между предметом и оценками.</p>
$ curl -s --data-urlencode $'grades=Химия: 4 12' http://localhost:8082/ | grep 'class="error"'
    <p class="error">Ошибка: Оценка 12 вне шкалы: допустимы значения от 1 до 10.</p>
```

Файлы вне `public/` из браузера недоступны:

```
$ curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8082/config.php
404
```

## Описание плейбука setup_test_server.yml

Плейбук состоит из одного сценария (play) для группы `webservers`. В блоке `vars` заданы три переменные: `site_title` (название сайта для комментария в конфигурации Apache), `gradebook_dir: /var/www/gradebook` (каталог проекта) и `php_version: "8.1"` (от неё зависит путь к `php.ini`). Названия задач написаны по-русски, все модули взяты из `ansible.builtin` и записаны полными именами (FQCN), чтобы было видно, откуда модуль.

Повышение прав (`become: true`) указано не для всего сценария, а у каждой задачи, которой оно нужно, и в комментарии к задаче сказано, зачем. Так из файла сразу видно, какие действия выполняются от root. В этом плейбуке root нужен всем задачам, потому что все они меняют систему, а в `deploy_gradebook.yml` и `configure_gradebook.yml` есть задачи без `become`.

1. **Установка веб-сервера Apache2.** Модуль `apt` с `name: apache2`, `state: present` и `update_cache: true`. Список пакетов в образе удалён после сборки, поэтому без `update_cache` apt не нашёл бы пакет. Модуль `apt` сам доустанавливает на сервер `python3-apt`, если его нет.
2. **Установка PHP и расширений.** Тот же модуль со списком пакетов:
   - `libapache2-mod-php` подключает PHP к Apache. При установке пакет сам включает модуль `php8.1`, отдельная команда `a2enmod` не нужна;
   - `php-mbstring` нужен для строк в UTF-8: названия предметов на кириллице;
   - `php-intl` даёт класс `NumberFormatter`, которым страница печатает средний балл с десятичной запятой.
3. **Настройка часового пояса PHP.** Модуль `lineinfile` в файле `/etc/php/8.1/apache2/php.ini` ищет строку по выражению `^;?date.timezone` и заменяет её на `date.timezone = Europe/Chisinau`. Знак `;?` нужен потому, что в исходном файле строка закомментирована: так она заменяется, а не добавляется второй раз. Это настройка PHP, которую требует задание: страница показывает время выкладки, и без неё PHP считал бы время в UTC. Задача уведомляет обработчик перезапуска.
4. **Запуск Apache2.** Модуль `service` с `state: started`. После установки пакета Apache в контейнере не работает: в образе Ubuntu есть файл `/usr/sbin/policy-rc.d` с командой `exit 101`, который запрещает пакетам запускать службы при установке. Поэтому при первом запуске эта задача получает статус `changed`. systemd в контейнере нет, поэтому модуль сам выбирает сценарий `/etc/init.d/apache2`.
5. **Каталог сайта.** Модуль `file` создаёт `/var/www/gradebook/public` с правами `0755`, на него указывает `DocumentRoot`.
6. **Файл виртуального хоста.** Модуль `template` собирает `/etc/apache2/sites-available/gradebook.conf` из шаблона `templates/gradebook.conf.j2` и уведомляет обработчик, если содержимое изменилось.
7. **Включение сайта gradebook.** Для включения сайта в Apache есть команда `a2ensite`, а встроенного модуля для неё в `ansible-core` нет, поэтому используется модуль `command`. Он всегда считает задачу изменившей сервер, и для идемпотентности результат сохраняется в `register: a2ensite_result`, а `changed_when` проверяет вывод: если в нём есть `already enabled`, сайт уже был включён, и задача получает статус `ok`. Точный текст сообщения я проверил на сервере (см. «Что я проверил заранее» в конце раздела ответов).
8. **Отключение сайта по умолчанию.** `a2dissite 000-default` с такой же проверкой по `already disabled`. Стандартный сайт тоже слушает порт 80, и без его отключения Apache отдавал бы страницу «It works!».

**Обработчик** `Перезапуск Apache2` вызывает модуль `service` с `state: restarted`. Обработчики выполняются один раз в конце сценария, сколько бы задач их ни уведомили. Выбран именно перезапуск, а не `reloaded`: изменение `php.ini` модуль `mod_php` читает только при старте Apache.

**Шаблон gradebook.conf.j2:**

```apache
<VirtualHost *:80>
    DocumentRoot {{ gradebook_dir }}/public

    <Directory {{ gradebook_dir }}/public>
        Require all granted
        DirectoryIndex index.php
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/gradebook_error.log
    CustomLog ${APACHE_LOG_DIR}/gradebook_access.log combined
</VirtualHost>
```

`{{ gradebook_dir }}` подставляет Jinja2 из переменной плейбука, а `${APACHE_LOG_DIR}` остаётся как есть: это переменная самого Apache из `/etc/apache2/envvars`. Наружу открыт только каталог `public`, поэтому `src/` и `config.php` из браузера недоступны. В начале шаблона стоит комментарий о том, что файл создаёт Ansible, и правки вручную будут перезаписаны.

### deploy_gradebook.yml

Плейбук этапа «Копирование файлов на сервер»:

1. **Проверка архива:** модуль `stat` с `delegate_to: localhost` проверяет файл `{{ playbook_dir }}/../gradebook.tar.gz` на управляющем узле, где его собрал конвейер. Права root для этого не нужны;
2. **Архив должен существовать:** модуль `assert` останавливает плейбук с понятным сообщением, если архива нет;
3. **Каталог приложения:** `file` создаёт `/var/www/gradebook`, если сервер почему-то не настроен;
4. **Распаковка архива на сервере:** модуль `unarchive` сам копирует архив с управляющего узла на сервер по SSH и распаковывает его в `/var/www/gradebook`. Владелец файлов `root`, группа `www-data`: Apache может их читать, но не может изменить.

Я выбрал архив и `unarchive`, а не модуль `synchronize`, потому что `synchronize` находится в коллекции `ansible.posix` и требует `rsync` на обеих машинах, а `unarchive` входит в `ansible-core`. Архив также переносится по SSH одним файлом.

### configure_gradebook.yml

Плейбук этапа «Настройка проекта на сервере»:

1. **Файл настроек config.php:** модуль `template` собирает файл из `templates/config.php.j2`:

   ```php
   return [
       'title' => '{{ site_title }}',
       'build' => '{{ build_number | default("вручную") }}',
       'deployed_at' => '{{ ansible_facts['date_time']['iso8601'] }}',
       'server' => '{{ inventory_hostname }}',
   ];
   ```

   `build_number` передаёт конвейер (`-e build_number=$BUILD_NUMBER`), а фильтр `default` подставляет «вручную», если плейбук запущен без него. Время выкладки берётся из факта `date_time`, который Ansible собрал о сервере (почему через `ansible_facts`, сказано в проблеме 2), а `inventory_hostname` равно имени сервера в инвентаре. Права `0640` и группа `www-data`: файл читает только Apache;
2. **Права на файлы:** модуль `file` с `recurse: true` назначает всем файлам проекта владельца `root` и группу `www-data`;
3. **Проверка страницы:** модуль `uri` запрашивает `http://localhost/` на самом сервере и ожидает код 200. Если Apache или PHP не работают, выкладка завершится ошибкой прямо в Jenkins, а не обнаружится позже в браузере. Эта задача выполняется без `become`.

Благодаря `config.php` страница сама показывает, какая сборка на сервере, и по ней легко проверить, что выкладка прошла.

## Результаты

Ниже приведён вывод итоговых сборок всех трёх заданий. Все они собирали коммит `eda70b2`. Из вывода убраны строки служебных команд git и маркеры `[Pipeline]`, пропуски отмечены `...`.

### lab05-gradebook-build, сборка №2

```
Running on ssh-agent1 in /home/jenkins/agent/workspace/lab05-gradebook-build
...
+ git log -1 --format=%h %an %s
eda70b2 Bordeniuc Ivan Add comments to Dockerfiles, playbooks and pipelines
+ cd lab05/gradebook
+ php --version
PHP 8.4.27 (cli) (built: Oct 21 2026 07:53:46) (NTS)
...
+ composer install --no-interaction --optimize-autoloader
Installing dependencies from lock file (including require-dev)
Verifying lock file contents can be installed on current platform.
Nothing to install, update or remove
Generating optimized autoload files
...
+ cd lab05/gradebook
+ vendor/bin/phpunit --testdox --log-junit build/junit.xml --testdox-html build/testdox.html
PHPUnit 10.5.66 by Sebastian Bergmann and contributors.

Runtime:       PHP 8.4.27
Configuration: /home/jenkins/agent/workspace/lab05-gradebook-build/lab05/gradebook/phpunit.xml

............                                                      12 / 12 (100%)

Time: 00:00.023, Memory: 8.00 MB

Grade Book (Bordeniuc\Gradebook\Tests\GradeBook)
 ✔ Оценка добавляется к предмету
 ✔ Средний балл по предмету округляется до двух знаков
 ✔ Общий средний балл считается по средним баллам предметов
 ✔ Оценка 0 не принимается
 ✔ Оценка 11 не принимается
 ✔ Пустое название предмета не принимается
 ✔ Средний балл по неизвестному предмету вызывает исключение
 ✔ Предметы со средним баллом ниже 5 считаются задолженностями
 ✔ У пустого журнала средний балл равен 0

Grade Text Parser (Bordeniuc\Gradebook\Tests\GradeTextParser)
 ✔ Правильный текст превращается в журнал с предметами и оценками
 ✔ Строка без двоеточия вызывает исключение с номером строки
 ✔ Пустые строки пропускаются

OK (12 tests, 17 assertions)
Recording test results
[Checks API] No suitable checks publisher found.
Archiving artifacts
Pipeline completed.
All stages completed successfully!
Finished: SUCCESS
```

Composer пишет `Nothing to install`, потому что рабочий каталог узла лежит в томе `jenkins_agent_volume`, и `vendor/` остался от сборки №1, в которой были установлены все 26 пакетов. Строка `[Checks API] No suitable checks publisher found.` не является ошибкой: плагин JUnit сообщает, что публиковать результаты в GitHub Checks некуда.

### lab05-test-server-setup, сборка №4

```
Running on ansible-control-node in /home/jenkins/agent/workspace/lab05-test-server-setup
...
+ git log -1 --format=%h %an %s
eda70b2 Bordeniuc Ivan Add comments to Dockerfiles, playbooks and pipelines
[ssh-agent] Using credentials ansible (Ключ Ansible для тестового сервера)
$ ssh-agent
...
Running ssh-add (command line suppressed)
[ssh-agent] Started.
+ cd lab05/ansible
+ mkdir -p /home/jenkins/.ssh
+ ssh-keyscan -t ed25519 test-server
# test-server:22 SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.18
+ ansible --version
ansible [core 2.20.10]
  config file = None
...
  executable location = /usr/local/bin/ansible
  python version = 3.12.3 (main, Aug 31 2026, 10:18:26) [GCC 13.3.0] (/opt/ansible/bin/python3)
...
+ ansible-playbook -i hosts.ini setup_test_server.yml

PLAY [Настройка тестового сервера для gradebook] *******************************

TASK [Gathering Facts] *********************************************************
ok: [test-server]

TASK [Установка веб-сервера Apache2] *******************************************
changed: [test-server]

TASK [Установка PHP и расширений] **********************************************
changed: [test-server]

TASK [Настройка часового пояса PHP] ********************************************
changed: [test-server]

TASK [Запуск Apache2] **********************************************************
changed: [test-server]

TASK [Каталог сайта] ***********************************************************
changed: [test-server]

TASK [Файл виртуального хоста] *************************************************
changed: [test-server]

TASK [Включение сайта gradebook] ***********************************************
changed: [test-server]

TASK [Отключение сайта по умолчанию] *******************************************
changed: [test-server]

RUNNING HANDLER [Перезапуск Apache2] *******************************************
changed: [test-server]

PLAY RECAP *********************************************************************
test-server                : ok=10   changed=9    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0   

$ ssh-agent -k
...
[ssh-agent] Stopped.
Тестовый сервер настроен.
Finished: SUCCESS
```

Строка `executable location = /usr/local/bin/ansible` показывает, что команда найдена по ссылке из `/usr/local/bin` (проблема 1). Обработчик `Перезапуск Apache2` выполнился один раз, хотя о нём сообщили четыре задачи. Повторный запуск (сборка №5) дал `ok=9 changed=0`: обработчик не вызывался, поэтому задач на одну меньше.

### lab05-gradebook-deploy, сборка №4

```
Running on ansible-control-node in /home/jenkins/agent/workspace/lab05-gradebook-deploy
...
+ git log -1 --format=%h %an %s
eda70b2 Bordeniuc Ivan Add comments to Dockerfiles, playbooks and pipelines
+ tar -czf lab05/gradebook.tar.gz -C lab05/gradebook src public
[ssh-agent] Using credentials ansible (Ключ Ansible для тестового сервера)
...
+ ansible-playbook -i hosts.ini deploy_gradebook.yml

PLAY [Копирование файлов gradebook на тестовый сервер] *************************

TASK [Gathering Facts] *********************************************************
ok: [test-server]

TASK [Проверка архива] *********************************************************
ok: [test-server -> localhost]

TASK [Архив должен существовать] ***********************************************
ok: [test-server] => {
    "changed": false,
    "msg": "All assertions passed"
}

TASK [Каталог приложения] ******************************************************
ok: [test-server]

TASK [Распаковка архива на сервере] ********************************************
changed: [test-server]

PLAY RECAP *********************************************************************
test-server                : ok=5    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0   
...
+ cd lab05/ansible
+ ansible-playbook -i hosts.ini configure_gradebook.yml -e build_number=4

PLAY [Настройка gradebook на тестовом сервере] *********************************

TASK [Gathering Facts] *********************************************************
ok: [test-server]

TASK [Файл настроек config.php] ************************************************
changed: [test-server]

TASK [Права на файлы] **********************************************************
changed: [test-server]

TASK [Проверка страницы] *******************************************************
ok: [test-server]

PLAY RECAP *********************************************************************
test-server                : ok=4    changed=2    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0   
...
Журнал оценок выложен на тестовый сервер.
Finished: SUCCESS
```

Задача `Проверка архива` выполнена на управляющем узле (`test-server -> localhost`), как задумано через `delegate_to`. Задача `Каталог приложения` получила `ok`, потому что каталог уже создал плейбук настройки. В строке запуска второго плейбука видно, что оболочка подставила номер сборки: `-e build_number=4`.

## Ответы на контрольные вопросы

### Какие преимущества даёт Ansible для настройки серверов?

Первое и главное преимущество: в плейбуке я записываю, каким сервер должен стать, и не думаю, через какие команды он к этому придёт. В lab01 я писал shell-скрипт `backup.sh`, и в нём каждая строка была командой, которую нужно выполнить именно в этом порядке; если какая-то команда уже была выполнена раньше, скрипт об этом не знает. В плейбуке я пишу «пакет `apache2` должен быть установлен», «файл `gradebook.conf` должен иметь такое содержимое», «служба должна работать», а как этого добиться, решает модуль. Такой подход называется декларативным, в отличие от императивного подхода скриптов.

Второе: плейбук одновременно является документацией сервера. Раньше настройку сервера пришлось бы описывать в отдельной инструкции: какие пакеты поставить, какой файл куда положить, какую строку изменить в `php.ini`. Теперь эта инструкция и есть `setup_test_server.yml`: названия задач читаются как пункты списка, а сам список выполняется. Инструкция не может устареть, потому что сервер настраивается именно по ней.

Третье: у Ansible большая библиотека модулей и коллекций. Для пакетов, файлов, служб, пользователей, шаблонов, архивов и HTTP-запросов есть готовые модули, которые проверяют текущее состояние и возвращают понятный результат. В этой работе мне хватило встроенных модулей `ansible.builtin`, а для баз данных, облаков и сетевого оборудования есть отдельные коллекции. Кроме того, Ansible не требует агента на сервере: достаточно SSH и Python, которые на Linux-серверах обычно уже есть.

Четвёртое: идемпотентность, то есть повторный запуск не меняет уже настроенный сервер. Это видно по статусам задач. При первом запуске `setup_test_server.yml` (сборка №4) итог был `ok=10 changed=9`: Ansible действительно устанавливал пакеты и создавал файлы. При втором запуске того же плейбука (сборка №5) итог был `ok=9 changed=0`: все задачи получили статус `ok`, обработчик перезапуска Apache не вызывался, и на сервере ничего не изменилось. Shell-скрипт без дополнительных проверок повторил бы все команды заново.

### Какие ещё модули Ansible существуют для управления конфигурацией?

В документации Ansible модули разделены на категории. Ниже модули, которые я не использовал в основных плейбуках, но которые подходят для управления конфигурацией.

**Работа с файлами.** `ansible.builtin.stat` возвращает сведения о файле (существует ли, размер, владелец, контрольная сумма); я использовал его в `deploy_gradebook.yml` для проверки архива. `ansible.builtin.fetch` делает обратное копированию: забирает файл с сервера на управляющий узел, например журнал ошибок Apache. `ansible.builtin.replace` заменяет все совпадения регулярного выражения в файле, в отличие от `lineinfile`, который работает с одной строкой. `ansible.builtin.assemble` собирает один файл конфигурации из набора фрагментов в каталоге.

**Пакеты.** `ansible.builtin.apt_repository` добавляет или удаляет репозитории APT; с его помощью можно было бы подключить PPA с более новой версией PHP.

**Базы данных.** `community.postgresql.postgresql_db` создаёт и удаляет базы PostgreSQL. Этот модуль находится не в `ansible-core`, а в коллекции `community.postgresql`, её нужно установить командой `ansible-galaxy collection install community.postgresql`.

**Системы контроля версий.** `ansible.builtin.subversion` получает код из репозитория Subversion (для Git есть `ansible.builtin.git`).

**Сетевые инструменты.** `ansible.builtin.uri` выполняет HTTP-запрос и проверяет ответ; я использовал его в `configure_gradebook.yml`, чтобы плейбук сам проверял, что страница отвечает кодом 200. `ansible.builtin.wait_for` ждёт, пока откроется порт или появится файл, это полезно после перезапуска службы.

Пример `wait_for`: дождаться, пока Apache начнёт слушать порт 80, но не дольше 30 секунд.

```yaml
- name: Ожидание порта 80
  ansible.builtin.wait_for:
    port: 80
    timeout: 30
```

Пример `replace`: заменить во всём файле `php.ini` ограничение размера загружаемого файла.

```yaml
- name: Размер загружаемых файлов
  become: true
  ansible.builtin.replace:
    path: /etc/php/8.1/apache2/php.ini
    regexp: '^upload_max_filesize = .*$'
    replace: 'upload_max_filesize = 8M'
```

Из перечисленных модулей только `postgresql_db` требует отдельной коллекции, остальные входят в `ansible-core` и работают на моём управляющем узле без установки чего-либо ещё.

### Какие проблемы возникли при создании Ansible-плейбука и как они были решены?

#### Проблема 1. ansible: not found в SSH-сессии Jenkins

**Что произошло.** Первая сборка задания `lab05-test-server-setup` дошла до этапа «Настройка тестового сервера» и остановилась на команде `ansible --version`:

```
+ ssh-keyscan -t ed25519 test-server
# test-server:22 SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.18
+ ansible --version
/home/jenkins/agent/workspace/lab05-test-server-setup@tmp/durable-457a2ca2/script.sh.copy: 5: ansible: not found
$ ssh-agent -k
...
ERROR: script returned exit code 127
Finished: FAILURE
```

При этом `docker compose exec ansible-agent ansible --version` работал (шаг 3 хода работы).

**Причина.** Ansible установлен в виртуальное окружение, и его команды лежат в `/opt/ansible/bin`. Этот каталог я добавил в `PATH` строкой `ENV PATH=...` в Dockerfile. Переменные `ENV` получает главный процесс контейнера и всё, что запускается через `docker exec`. Jenkins же подключается к узлу по SSH, и sshd создаёт для сессии новое окружение со стандартным `PATH`. Это видно в журнале подключения узла (шаг 7): `PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin`, каталога `/opt/ansible/bin` там нет. Код выхода 127 означает «команда не найдена».

**Как решено.** В `Dockerfile.ansible_agent` добавлена строка, которая создаёт ссылки на команды Ansible в `/usr/local/bin`, а этот каталог в стандартном `PATH` есть:

```dockerfile
RUN ln -s /opt/ansible/bin/ansible /opt/ansible/bin/ansible-playbook /opt/ansible/bin/ansible-galaxy /usr/local/bin/
```

Строку `ENV PATH` я оставил: она по-прежнему полезна для `docker compose exec`. После `docker compose up -d --build ansible-agent` контейнер был пересоздан, узел переподключился, и сборка №2 прошла. В её выводе видно `executable location = /usr/local/bin/ansible`. Ключ хоста узла при этом не изменился: слой образа с установкой openssh-server взят из кеша сборки, поэтому вставленный в Jenkins ключ подошёл.

Другие способы, которые я рассматривал: указать полный путь `/opt/ansible/bin/ansible-playbook` в каждом конвейере (тогда путь окружения дублировался бы в трёх файлах) или задать `PATH` в настройках узла Jenkins (тогда часть настройки жила бы не в репозитории, а в интерфейсе Jenkins). Ссылки в образе решают задачу в одном месте.

#### Проблема 2. Предупреждение об устаревшем обращении к фактам

**Что произошло.** Первая сборка `lab05-gradebook-deploy` завершилась успешно, но на задаче, которая создаёт `config.php`, Ansible вывел предупреждение:

```
TASK [Файл настроек config.php] ************************************************
[WARNING]: Deprecation warnings can be disabled by setting `deprecation_warnings=False` in ansible.cfg.
[DEPRECATION WARNING]: INJECT_FACTS_AS_VARS default to `True` is deprecated, top-level facts will not be auto injected after the change. This feature will be removed from ansible-core version 2.24.
Origin: /home/jenkins/agent/workspace/lab05-gradebook-deploy/lab05/ansible/templates/config.php.j2

Use `ansible_facts["fact_name"]` (no `ansible_` prefix) instead.

changed: [test-server]
```

**Причина.** В шаблоне `config.php.j2` время выкладки бралось из переменной `ansible_date_time`. Ansible собирает факты о сервере в словарь `ansible_facts`, а для удобства по умолчанию дублирует каждый факт отдельной переменной с префиксом `ansible_`. В ansible-core 2.20 это дублирование объявлено устаревшим, а в версии 2.24 его отключат. Тогда переменная `ansible_date_time` исчезнет, и шаблон перестанет работать. Во многих учебных примерах используется именно старая запись, поэтому я написал её по привычке.

**Как решено.** В шаблоне я заменил обращение на рекомендованное:

```
'deployed_at' => '{{ ansible_facts['date_time']['iso8601'] }}',
```

Отключать предупреждение через `deprecation_warnings=False` я не стал: оно указывало на реальную проблему, которая проявилась бы при обновлении Ansible. Следующие выкладки, включая итоговую сборку №4, прошли без предупреждений.

#### Что я проверил заранее, чтобы не получить проблем

- Точный текст вывода `a2ensite` и `a2dissite` при повторном вызове, от которого зависит `changed_when`. На сервере после настройки:

  ```
  $ docker compose exec test-server sh -c 'a2ensite gradebook; a2dissite 000-default'
  Site gradebook already enabled
  Site 000-default already disabled
  ```

  Поэтому в условиях стоят подстроки `already enabled` и `already disabled`, и повторный запуск даёт `changed=0`.
- Локаль `ro_MD` в ICU 70.1 на Ubuntu 22.04 есть, и `NumberFormatter` печатает `9,00`, так что запасной вариант с локалью `ro` не понадобился.

## Выводы

В этой работе к стенду из lab04 добавились управляющий узел Ansible и тестовый сервер, а Jenkins получил три конвейера, которые вместе проходят путь от теста до работающей страницы: сборка проверяет код, настройка готовит сервер, выкладка переносит на него проект и сама проверяет ответ страницы. Каждый шаг описан в файле репозитория, поэтому стенд можно поднять заново и получить тот же результат. Повторный запуск настройки с итогом `changed=0` показал на деле: если сервер уже в нужном виде, Ansible ничего на нём не трогает.

Больше всего времени заняли не сами плейбуки, а окружение, в котором они выполняются: SSH-сессия Jenkins видит другой `PATH`, чем `docker exec`, а ключ для Ansible нужно передать так, чтобы он не остался на диске агента. Шаг `sshagent` и три отдельные пары ключей решили вторую задачу, ссылки в `/usr/local/bin` решили первую. Предупреждение о фактах научило меня читать вывод успешных сборок так же внимательно, как вывод упавших.
