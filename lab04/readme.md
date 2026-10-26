# Лабораторная работа №4. Настройка Jenkins для автоматизации задач DevOps

## Цель работы

Научиться настраивать Jenkins для автоматизации задач DevOps: поднять контроллер Jenkins и SSH-агент в Docker Compose, подключить агент к контроллеру и создать конвейер (pipeline), который устанавливает зависимости PHP-проекта и запускает его модульные тесты.

## Задание

1. Создать в репозитории каталог `lab04` для всех файлов работы.
2. Описать в `docker-compose.yml` два сервиса: контроллер Jenkins (`jenkins-controller`) и SSH-агент (`ssh-agent`), а также тома `jenkins_home`, `jenkins_agent_volume` и сеть `jenkins-network`.
3. Запустить контроллер и выполнить первоначальную настройку Jenkins по инструкциям на экране.
4. Создать каталог `secrets` и SSH-ключи командой `ssh-keygen -f jenkins_agent_ssh_key`.
5. Написать `Dockerfile` для SSH-агента на основе `jenkins/ssh-agent` с установкой `php-cli`.
6. Создать файл `.env` с переменной `JENKINS_AGENT_SSH_PUBKEY` и перезапустить проект Docker Compose.
7. Убедиться, что установлен плагин SSH Agents (SSH Build Agents), добавить в Jenkins учётные данные с закрытым ключом (пользователь `jenkins`).
8. Создать постоянный узел `ssh-agent1` с меткой `php-agent`, каталогом `/home/jenkins/agent`, запуском по SSH на хост `ssh-agent`.
9. Взять PHP-проект с модульными тестами и создать для него pipeline по шаблону Jenkinsfile из задания.
10. Убедиться, что pipeline выполняется успешно и тесты проходят.
11. Оформить отчёт `readme.md` с описанием проекта, шагов настройки и ответами на контрольные вопросы.

## Используемые технологии

- **Jenkins 2.580.1 LTS** (образ `jenkins/jenkins:lts`, Debian 13, Java 21) - сервер автоматизации. Хранит задания, показывает веб-интерфейс и раздаёт сборки агентам.
- **Docker Compose** - описывает оба контейнера, их тома и общую сеть в одном файле, поэтому весь стенд поднимается одной командой.
- **jenkins/ssh-agent:jdk21** (Debian 13, Java 21, git 2.47) - официальный образ агента с сервером sshd. Java нужна агенту только для процесса remoting, через который контроллер управляет сборкой.
- **PHP 8.4.27** - интерпретатор из репозитория Debian 13 (пакет `php-cli`), на нём выполняются Composer и тесты.
- **Composer 2.10.3** - менеджер зависимостей PHP. Устанавливает PHPUnit в каталог `vendor/` по файлу `composer.lock`.
- **PHPUnit 10.5.66** - фреймворк модульного тестирования. Ветку 10.5 мы использовали в курсе «Программирование на PHP», она поддерживает PHP 8.1+ и атрибут `#[TestDox]`.
- **Плагины Jenkins**: Pipeline (декларативные конвейеры), Git 5.11.0 (получение Jenkinsfile и кода из репозитория), SSH Build Agents 3.1097.v868116049892 (запуск агентов по SSH), Credentials и SSH Credentials (хранение закрытого ключа).

## Описание проекта gradebook

Для работы я написал небольшой проект `gradebook` - электронный журнал оценок студента. Оценки ставятся по 10-балльной шкале, принятой в Молдове: от 1 до 10, где 5 - минимальная положительная оценка. Если средний балл по предмету ниже 5, предмет считается задолженностью.

Структура проекта:

```
gradebook/
├── composer.json        описание пакета bordeniuc/gradebook и зависимостей
├── composer.lock        точные версии PHPUnit и его зависимостей (26 пакетов)
├── phpunit.xml          настройки PHPUnit
├── src/
│   ├── GradeBook.php      класс журнала
│   └── GradeException.php исключение журнала
└── tests/
    └── GradeBookTest.php  9 модульных тестов
```

Пространство имён кода - `Bordeniuc\Gradebook`, тестов - `Bordeniuc\Gradebook\Tests`. Автозагрузка классов настроена по стандарту PSR-4 в `composer.json`. В `require` указано только `"php": ">=8.1"`, а PHPUnit `^10.5` вынесен в `require-dev`, потому что он нужен только для разработки и проверки.

### Класс GradeBook

Все методы описаны PHPDoc-комментариями на русском языке.

| Метод | Что делает |
|---|---|
| `addGrade(string $subject, int $grade): void` | добавляет оценку по предмету. Пробелы по краям названия отбрасываются. Если название пустое или оценка не входит в диапазон 1-10, выбрасывается `GradeException` с русским сообщением |
| `subjects(): array` | возвращает список предметов в порядке добавления первой оценки |
| `averageFor(string $subject): float` | средний балл по предмету, округлённый до двух знаков. Для предмета без оценок выбрасывается `GradeException` |
| `overallAverage(): float` | общий средний балл: среднее значение средних баллов по предметам (каждый предмет весит одинаково). Для пустого журнала возвращает `0.0` |
| `failedSubjects(): array` | список задолженностей: предметы со средним баллом ниже 5 |

Границы шкалы и проходной балл вынесены в константы `MIN_GRADE`, `MAX_GRADE` и `PASSING_AVERAGE`, чтобы в коде не было «магических чисел».

`GradeException` - это `final class GradeException extends \InvalidArgumentException`. Отдельный класс исключения позволяет в тестах проверять, что ошибку выбросил именно журнал, а не PHP.

### Модульные тесты

В файле `tests/GradeBookTest.php` 9 тестов. У каждого есть атрибут `#[TestDox('...')]` с русским предложением, а запуск с ключом `--testdox` печатает в журнал сборки эти предложения. Поэтому по выводу Jenkins сразу видно, какое поведение проверено.

| № | TestDox | Что проверяет |
|---|---|---|
| 1 | Оценка добавляется к предмету | после `addGrade('Математика', 9)` предмет есть в списке, а средний балл равен 9.0 |
| 2 | Средний балл по предмету округляется до двух знаков | оценки 8, 9, 9 дают 8.67 (а не 8.666...) |
| 3 | Общий средний балл считается по средним баллам предметов | 10 по информатике и 6, 8 по истории дают (10 + 7) / 2 = 8.5, а не 8.0 |
| 4 | Оценка 0 не принимается | `GradeException` для оценки ниже шкалы |
| 5 | Оценка 11 не принимается | `GradeException` для оценки выше шкалы |
| 6 | Пустое название предмета не принимается | название из пробелов после `trim` пустое, ожидается `GradeException` |
| 7 | Средний балл по неизвестному предмету вызывает исключение | `averageFor('Химия')` для пустого журнала |
| 8 | Предметы со средним баллом ниже 5 считаются задолженностями | химия со средним 4.5 - задолженность, биология с ровно 5 и география с 9 - нет |
| 9 | У пустого журнала средний балл равен 0 | `overallAverage()` возвращает `0.0` |

Исключения проверяются через `$this->expectException(GradeException::class)`. Метод `setUp()` создаёт новый пустой журнал перед каждым тестом, поэтому тесты не зависят друг от друга.

### phpunit.xml

```xml
<phpunit xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:noNamespaceSchemaLocation="vendor/phpunit/phpunit/phpunit.xsd"
         bootstrap="vendor/autoload.php"
         cacheDirectory=".phpunit.cache"
         colors="false"
         failOnWarning="true">
```

- схема берётся из установленного PHPUnit, поэтому она всегда соответствует версии 10.5;
- `bootstrap="vendor/autoload.php"` подключает автозагрузчик Composer;
- `colors="false"` отключает цветной вывод: в журнале Jenkins escape-коды цветов выглядели бы как мусор;
- `failOnWarning="true"`: если PHPUnit выдал предупреждение (например, об устаревшей настройке), запуск тоже считается проваленным, а не только при упавшем тесте;
- в набор `Gradebook` попадают все файлы `*Test.php` из каталога `tests`.

## Описание файлов

Итоговая структура каталога:

```
lab04/
├── Dockerfile
├── Jenkinsfile
├── docker-compose.yml
├── gradebook/
│   ├── composer.json
│   ├── composer.lock
│   ├── phpunit.xml
│   ├── src/{GradeBook.php, GradeException.php}
│   └── tests/GradeBookTest.php
├── readme.md
└── secrets/
    └── jenkins_agent_ssh_key.pub   (закрытый ключ только локально)
(.env создаётся локально и в git не попадает)
```

Во всех трёх инфраструктурных файлах перед почти каждой строкой стоит комментарий на русском языке, поэтому их можно читать и без отчёта.

### docker-compose.yml

Файл повторяет конфигурацию из задания. Я добавил только комментарии, ни одно значение не изменено.

Контроллер:

```yaml
  jenkins-controller:
    image: jenkins/jenkins:lts
    container_name: jenkins-controller
    ports:
      - "8080:8080"
      - "50000:50000"
    volumes:
      - jenkins_home:/var/jenkins_home
    networks:
      - jenkins-network
```

- `8080` - веб-интерфейс Jenkins;
- `50000` - порт для входящих (inbound) агентов. SSH-агенту он не нужен, потому что здесь соединение открывает сам контроллер, но порт оставлен, как в задании;
- в томе `jenkins_home` хранятся настройки, плагины, учётные данные, задания и история сборок, поэтому они переживают пересоздание контейнера.

Агент:

```yaml
  ssh-agent:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ssh-agent
    environment:
      - JENKINS_AGENT_SSH_PUBKEY=${JENKINS_AGENT_SSH_PUBKEY}
    volumes:
      - jenkins_agent_volume:/home/jenkins/agent
    depends_on:
      - jenkins-controller
    networks:
      - jenkins-network
```

- образ собирается из `Dockerfile` в этом же каталоге;
- `${JENKINS_AGENT_SSH_PUBKEY}` Docker Compose подставляет из файла `.env`. При старте контейнера образ `jenkins/ssh-agent` берёт значение этой переменной и делает его разрешённым ключом пользователя `jenkins`. Поэтому вход по парному закрытому ключу sshd пропускает, а любой другой ключ отклоняет;
- том `jenkins_agent_volume` подключён в `/home/jenkins/agent` - это рабочий каталог узла (remote root directory). В нём лежат `remoting.jar` и рабочие каталоги заданий (`workspace/lab04-gradebook`);
- `depends_on` запускает агент после контроллера.

Оба контейнера подключены к сети `jenkins-network` (драйвер `bridge`). Внутри пользовательской сети Docker работает встроенный DNS, поэтому контроллер находит агента по имени сервиса `ssh-agent`. Именно это имя указывается в поле Host узла.

### Dockerfile

```dockerfile
FROM jenkins/ssh-agent:jdk21

RUN apt-get update && apt-get install -y php-cli php-xml php-mbstring unzip && rm -rf /var/lib/apt/lists/*

ADD https://getcomposer.org/download/2.10.3/composer.phar /usr/local/bin/composer

RUN chmod 755 /usr/local/bin/composer
```

Пояснения по строкам:

- `jenkins/ssh-agent:jdk21` - официальный образ агента, в нём уже есть sshd, git и Java. Тег `jdk21` указан явно. Сначала я взял `jdk17`, но контроллер не смог запустить на нём агент (см. проблему 3 в конце отчёта);
- `php-cli` - пакет из задания. В Debian 13 это PHP 8.4;
- `php-xml` - расширения `dom`, `xml`, `xmlwriter`. Без них Composer отказывается ставить PHPUnit (проблема 2);
- `php-mbstring` - расширение для строк в UTF-8, тоже входит в требования PHPUnit;
- `unzip` - Composer скачивает пакеты в zip-архивах и распаковывает их этой утилитой;
- `rm -rf /var/lib/apt/lists/*` удаляет списки пакетов после установки и уменьшает образ;
- `ADD <url> <путь>` скачивает файл во время сборки образа. Так в образ попадает конкретная версия Composer 2.10.3 одним файлом `composer.phar`, без установщика и без `curl` (его в образе нет). Файл назван `composer`, поэтому команда вызывается без расширения;
- `chmod 755`. Я проверил собранный без этой строки образ: файл, скачанный через `ADD` по URL, получает права `-rw-------` и принадлежит root, поэтому пользователь `jenkins` получает `sh: 1: composer: Permission denied`. После `chmod 755` его могут читать и запускать все пользователи.

Проверка образа после сборки:

```
$ docker exec ssh-agent sh -c 'java -version 2>&1 | head -1; php -r "echo PHP_VERSION, PHP_EOL;"; composer --version'
openjdk version "21.0.12.1" 2026-08-18 LTS
8.4.27
Composer version 2.10.3 2026-08-27 13:34:23
```

### Jenkinsfile

Файл построен по шаблону из задания: те же этапы `Install Dependencies` и `Test`, те же сообщения `echo` и тот же блок `post`. Добавлены только команды внутри этапов:

```groovy
stage('Install Dependencies') {
    steps {
        echo 'Preparing project...'
        sh '''
            cd lab04/gradebook
            php --version
            composer --version
            composer install --no-interaction --optimize-autoloader
        '''
    }
}

stage('Test') {
    steps {
        echo 'Running tests...'
        sh '''
            cd lab04/gradebook
            vendor/bin/phpunit --testdox
        '''
    }
}
```

- `agent { label 'php-agent' }` - Jenkins ищет свободный исполнитель на узле, у которого есть метка `php-agent`. Такая метка стоит только у `ssh-agent1`, поэтому туда и уходит сборка. На контроллере PHP нет, и это правильно: контроллер не должен выполнять сборки;
- шаг `sh '''...'''` выполняет несколько команд в одной оболочке, поэтому `cd lab04/gradebook` действует на следующие строки. Каждая команда печатается в журнале со знаком `+`;
- `php --version` и `composer --version` выводят версии в журнал сборки, чтобы по журналу было видно, в каком окружении шли тесты;
- `composer install` ставит пакеты строго по `composer.lock`, поэтому на агенте те же версии, что и у меня локально. `--no-interaction` запрещает вопросы (их некому задать), `--optimize-autoloader` строит карту классов;
- `vendor/bin/phpunit --testdox` запускает тесты. Если хотя бы один тест упадёт, PHPUnit вернёт ненулевой код выхода, шаг `sh` завершится ошибкой, и сработает блок `failure`;
- блок `post`: `always` выполняется всегда, `success` - только при успехе, `failure` - при ошибке любого этапа.

Отдельный этап checkout писать не нужно: декларативный pipeline сам выполняет этап `Declarative: Checkout SCM` и клонирует тот же репозиторий, из которого взят Jenkinsfile.

### .gitignore и каталог secrets

В корневой `.gitignore` добавлены строки:

```
# lab04: private SSH key of the Jenkins agent (public key is committed)
lab04/secrets/jenkins_agent_ssh_key

# lab04: Composer dependencies and PHPUnit cache
lab04/gradebook/vendor/
lab04/gradebook/.phpunit.cache/
```

Файл `.env` уже исключён правилом `.env` из лабораторной работы №2, оно действует во всех каталогах репозитория.

В репозитории лежит только открытый ключ `secrets/jenkins_agent_ssh_key.pub`. Его публиковать безопасно: по открытому ключу нельзя восстановить закрытый, он только позволяет серверу проверить подпись владельца закрытого ключа. Этот же ключ всё равно виден каждому, кто запустит контейнер агента (он лежит в `authorized_keys`). Закрытый ключ `jenkins_agent_ssh_key` - это фактически пароль для входа на агент, поэтому он хранится только на моём компьютере и в учётных данных Jenkins.

Проверка, что git действительно не видит секреты и временные файлы:

```
$ git check-ignore -v lab04/secrets/jenkins_agent_ssh_key lab04/.env lab04/gradebook/vendor/ lab04/gradebook/.phpunit.cache/
.gitignore:15:lab04/secrets/jenkins_agent_ssh_key	lab04/secrets/jenkins_agent_ssh_key
.gitignore:9:.env	lab04/.env
.gitignore:18:lab04/gradebook/vendor/	lab04/gradebook/vendor/
.gitignore:19:lab04/gradebook/.phpunit.cache/	lab04/gradebook/.phpunit.cache/
```

## Ход работы

### 1. Создание SSH-ключей

В каталоге `lab04` выполнил команду из задания, добавив комментарий ключа:

```bash
mkdir secrets
cd secrets
ssh-keygen -f jenkins_agent_ssh_key -C "jenkins-agent-lab04"
```

Passphrase оставил пустой, дважды нажав Enter. Ключ будет использовать сам Jenkins при каждом подключении к агенту, а не человек за клавиатурой, так что фразу всё равно некому было бы вводить.

- `-f jenkins_agent_ssh_key` - имя файла закрытого ключа, открытый получает имя `jenkins_agent_ssh_key.pub`;
- `-C "jenkins-agent-lab04"` - комментарий в конце открытого ключа. По умолчанию `ssh-keygen` пишет туда `пользователь@имя-компьютера`, а мне не нужно, чтобы имя моего компьютера попало в репозиторий. По комментарию сразу видно, для чего ключ;

Результат:

```
secrets/
├── jenkins_agent_ssh_key       закрытый ключ (права 600, в git не попадает)
└── jenkins_agent_ssh_key.pub   открытый ключ (ssh-ed25519 AAAA... jenkins-agent-lab04)
```

### 2. Файл .env

Файл `.env` создаётся в каталоге `lab04` рядом с `docker-compose.yml` одной командой:

```bash
echo "JENKINS_AGENT_SSH_PUBKEY=$(cat secrets/jenkins_agent_ssh_key.pub)" > .env
```

Содержимое получается таким (одна строка):

```
JENKINS_AGENT_SSH_PUBKEY=ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEm/zBWReJcVMrqdGBDrYeOAje1j4MeRzbHLxz4MS+vg jenkins-agent-lab04
```

Шаблон `.env.example` я не делал: в `.env` всего одна переменная, и её значение полностью получается командой выше из файла, который уже есть в репозитории.

### 3. Запуск контроллера Jenkins

Первый запуск `docker compose up -d` завершился ошибкой, потому что порт 8080 был занят:

```
Error response from daemon: ... Bind for 0.0.0.0:8080 failed: port is already allocated
```

Проверил, какой контейнер держит порт:

```
$ docker ps --filter "publish=8080"
CONTAINER ID   IMAGE            NAMES        PORTS
7d863e8be8ba   php:8.3-apache   php_apache   0.0.0.0:8080->80/tcp, [::]:8080->80/tcp
```

Это `php_apache` - сервис курсов валют `lab02prep` из лабораторных работ №2 и №3. Можно было опубликовать Jenkins на другом порту (например, `"8081:8080"`), но задание требует `http://localhost:8080`, поэтому я оставил порт 8080 и на время работы остановил `php_apache` (`docker stop php_apache`). Подробнее - в проблеме 1.

После этого стенд поднялся:

```bash
docker compose up -d --build
```

Пароль для разблокировки Jenkins:

```bash
docker exec jenkins-controller cat /var/jenkins_home/secrets/initialAdminPassword
```

Дальше на `http://localhost:8080`:

1. Ввёл пароль из `initialAdminPassword` на странице «Unlock Jenkins».
2. Выбрал «Install suggested plugins». Мастер установил 19 рекомендуемых плагинов вместе с зависимостями (Pipeline, Git, SSH Build Agents, Credentials Binding, Timestamper, Pipeline Graph View и другие).
3. Создал учётную запись администратора `bordeniuc`.
4. Оставил Jenkins URL `http://localhost:8080/` и нажал «Start using Jenkins».

Версия Jenkins видна в нижнем правом углу интерфейса: **Jenkins 2.580.1**.

### 4. Проверка плагина SSH Build Agents

В задании плагин называется «SSH Agents Plugin», сейчас он называется **SSH Build Agents** (идентификатор `ssh-slaves`). В Manage Jenkins > Plugins > Installed plugins он есть в списке, версия 3.1097.v868116049892. Он входит в рекомендуемый набор, поэтому отдельно ставить его не пришлось. Именно этот плагин добавляет способ запуска «Launch agents via SSH».

### 5. Учётные данные

Manage Jenkins > Credentials > System > Global credentials (unrestricted) > Add Credentials:

| Поле | Значение |
|---|---|
| Kind | SSH Username with private key |
| Scope | Global |
| ID | `jenkins_agent_ssh_key` |
| Description | Закрытый ключ для подключения к ssh-agent |
| Username | `jenkins` |
| Private Key | Enter directly, содержимое файла `secrets/jenkins_agent_ssh_key` целиком, вместе со строками `-----BEGIN OPENSSH PRIVATE KEY-----` и `-----END OPENSSH PRIVATE KEY-----` |
| Passphrase | пусто |

ID задал сам, а не оставил автоматический UUID: по понятному ID проще найти ключ в настройках узла и в `credentials.xml`.

### 6. Создание узла ssh-agent1

Manage Jenkins > Nodes > New Node, имя `ssh-agent1`, тип **Permanent Agent**. Поля:

| Поле | Значение | Зачем |
|---|---|---|
| Description | SSH-агент с PHP для лабораторной работы №4 | видно в списке узлов |
| Number of executors | 2 | две сборки могут идти на агенте одновременно |
| Remote root directory | `/home/jenkins/agent` | совпадает с томом `jenkins_agent_volume` |
| Labels | `php-agent` | по этой метке Jenkinsfile выбирает агент |
| Usage | Use this node as much as possible | значение по умолчанию |
| Launch method | Launch agents via SSH | способ из плагина SSH Build Agents |
| Host | `ssh-agent` | имя сервиса в сети `jenkins-network` |
| Credentials | `jenkins (Закрытый ключ для подключения к ssh-agent)` | ключ из шага 5 |
| Host Key Verification Strategy | Manually provided key Verification Strategy | см. ниже |
| SSH Key | `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA...` (ключ хоста агента) | см. ниже |
| Port (Advanced) | 22 | по умолчанию |
| Availability | Keep this agent online as much as possible | по умолчанию |

**Проверка ключа хоста.** Пользователь проверяет сервер по ключу хоста так же, как сервер проверяет пользователя по `authorized_keys`. Так клиент убеждается, что подключается к настоящему агенту, а не к подменённому. У плагина SSH Build Agents четыре стратегии:

- **Known hosts file Verification Strategy** - ключ ищется в файле `~/.ssh/known_hosts` на контроллере. В контейнере контроллера такого файла нет, его пришлось бы заполнять командой `ssh-keyscan`;
- **Manually provided key Verification Strategy** - ключ хоста вставляется в настройки узла вручную, и подключение разрешается только к серверу с этим ключом;
- **Manually trusted key Verification Strategy** - при первом подключении Jenkins запоминает ключ, но (с флажком «Require manual verification») ждёт, пока администратор подтвердит его в журнале узла;
- **Non verifying Verification Strategy** - ключ не проверяется совсем. Это проще всего, но тогда любой, кто подменит хост `ssh-agent`, получит сборки.

Я выбрал **Manually provided key**: это строгая проверка, и при этом видно, откуда взят ключ. Ключ хоста я взял прямо из контейнера агента:

```bash
docker exec ssh-agent cat /etc/ssh/ssh_host_ed25519_key.pub
```

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA...(ключ)... root@<id контейнера>
```

В поле SSH Key вставил первые две части строки: тип `ssh-ed25519` и сам ключ (комментарий `root@...` не нужен). Ключ типа ed25519 плагин принял, в журнале узла появилась строка:

```
[SSH] SSH host key matched the key required for this connection. Connection will be allowed.
```

После сохранения узел подключился. Конец журнала узла (Nodes > ssh-agent1 > Log):

```
[SSH] Opening SSH connection to ssh-agent:22.
[SSH] SSH host key matched the key required for this connection. Connection will be allowed.
[SSH] Authentication successful.
[SSH] The remote user's environment is:
...
[SSH] Starting sftp client.
[SSH] Copying latest remoting.jar...
...
[SSH] Starting agent process: cd "/home/jenkins/agent" && java  -jar remoting.jar -workDir /home/jenkins/agent -jar-cache /home/jenkins/agent/remoting/jarCache
...
<===[JENKINS REMOTING CAPACITY]===>   channel started
Remoting version: 3386.v353e57a_1b_ea_0
Launcher: SSHLauncher
Communication Protocol: Standard in/out
This is a Unix agent
Agent successfully connected and online
```

Отсюда видна вся схема: контроллер входит по SSH пользователем `jenkins`, копирует на агент `remoting.jar`, запускает его через `java` и дальше общается с агентом через стандартный ввод и вывод этого процесса.

### 7. Создание pipeline

New Item > имя `lab04-gradebook` > тип **Pipeline**. Поля:

| Поле | Значение |
|---|---|
| Description | Сборка и модульные тесты PHP-проекта gradebook (лабораторная работа №4) |
| Definition | Pipeline script from SCM |
| SCM | Git |
| Repository URL | `https://github.com/srulimoisovich/automation.git` |
| Credentials | - none - (репозиторий публичный) |
| Branch Specifier | `*/lab04` |
| Script Path | `lab04/Jenkinsfile` |
| Lightweight checkout | включён (по умолчанию) |

С «Pipeline script from SCM» Jenkinsfile хранится в git вместе с кодом: любое изменение конвейера проходит через коммит, и его историю видно в `git log`. Lightweight checkout позволяет контроллеру прочитать только сам `Jenkinsfile`, не клонируя весь репозиторий. Полное клонирование потом выполняется уже на агенте.

### 8. Запуск сборки

На странице задания нажал **Build Now**. Сборка №1 прошла успешно, все тесты зелёные. Полный журнал - в следующем разделе.

## Результат выполнения pipeline

Журнал сборки (Console Output), сокращён. Строки получения кода из git заменены на `...`, длинный список пакетов Composer тоже сокращён:

```
Started by user bordeniuc
...
[Pipeline] Start of Pipeline
[Pipeline] node
Running on ssh-agent1 in /home/jenkins/agent/workspace/lab04-gradebook
[Pipeline] {
[Pipeline] stage
[Pipeline] { (Declarative: Checkout SCM)
[Pipeline] checkout
...
Checking out Revision 4c67d3f11ee13aca232742223fdf7c61dc3985c0 (refs/remotes/origin/lab04)
Commit message: "Add comments to docker-compose.yml, Dockerfile and Jenkinsfile"
First time build. Skipping changelog.
[Pipeline] }
[Pipeline] // stage
[Pipeline] withEnv
[Pipeline] {
[Pipeline] stage
[Pipeline] { (Install Dependencies)
[Pipeline] echo
Preparing project...
[Pipeline] sh
+ cd lab04/gradebook
+ php --version
PHP 8.4.27 (cli) (built: Oct 21 2026 07:53:46) (NTS)
Copyright (c) The PHP Group
Built by Debian
Zend Engine v4.4.27, Copyright (c) Zend Technologies
    with Zend OPcache v8.4.27, Copyright (c), by Zend Technologies
+ composer --version
Composer version 2.10.3 2026-08-27 13:34:23
PHP version 8.4.27 (/usr/bin/php8.4)
Run the "diagnose" command to get more detailed diagnostics output.
+ composer install --no-interaction --optimize-autoloader
Installing dependencies from lock file (including require-dev)
Verifying lock file contents can be installed on current platform.
Package operations: 26 installs, 0 updates, 0 removals
  - Downloading sebastian/version (4.0.1)
...
  - Downloading phpunit/phpunit (10.5.66)
  - Installing sebastian/version (4.0.1): Extracting archive
...
  - Installing phpunit/phpunit (10.5.66): Extracting archive
Generating optimized autoload files
24 packages you are using are looking for funding.
Use the `composer fund` command to find out more!
[Pipeline] }
[Pipeline] // stage
[Pipeline] stage
[Pipeline] { (Test)
[Pipeline] echo
Running tests...
[Pipeline] sh
+ cd lab04/gradebook
+ vendor/bin/phpunit --testdox
PHPUnit 10.5.66 by Sebastian Bergmann and contributors.

Runtime:       PHP 8.4.27
Configuration: /home/jenkins/agent/workspace/lab04-gradebook/lab04/gradebook/phpunit.xml

.........                                                           9 / 9 (100%)

Time: 00:00.001, Memory: 8.00 MB

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

OK (9 tests, 10 assertions)
[Pipeline] }
[Pipeline] // stage
[Pipeline] stage
[Pipeline] { (Declarative: Post Actions)
[Pipeline] echo
Pipeline completed.
[Pipeline] echo
All stages completed successfully!
[Pipeline] }
[Pipeline] // stage
[Pipeline] }
[Pipeline] // withEnv
[Pipeline] }
[Pipeline] // node
[Pipeline] End of Pipeline
Finished: SUCCESS
```

Что видно по журналу:

- сборка шла на узле `ssh-agent1` в каталоге `/home/jenkins/agent/workspace/lab04-gradebook`, то есть в томе `jenkins_agent_volume`;
- Jenkins собрал коммит `4c67d3f` из ветки `lab04`;
- Composer установил 26 пакетов строго по `composer.lock`, среди них PHPUnit 10.5.66;
- все 9 тестов прошли (10 проверок), их названия выведены русскими предложениями из `#[TestDox]`;
- сработали блоки `post` `always` и `success`, итог - `Finished: SUCCESS`.

## Ответы на контрольные вопросы

### Преимущества Jenkins для автоматизации задач DevOps

**Непрерывная интеграция.** Jenkins проверяет проект сразу после изменения кода. Если бы я сломал, например, округление в `averageFor`, тест №2 упал бы в ближайшей сборке, и ошибка нашлась бы через минуты после коммита, а не перед сдачей работы.

**Нет ручной рутины.** Без Jenkins мне пришлось бы каждый раз заходить в контейнер, вызывать `composer install` и `vendor/bin/phpunit` и смотреть на результат. Теперь эта последовательность записана в Jenkinsfile один раз и выполняется одной кнопкой (или автоматически по событию из репозитория). Причём сам Jenkinsfile хранится в git рядом с кодом, и если я поменяю шаги сборки, это будет обычный коммит с понятной историей.

**История и журналы.** Jenkins сохраняет каждую сборку: кто и когда её запустил, какой коммит собран, полный журнал и результат. По журналу сборки №1 видно версии PHP, Composer и PHPUnit, то есть результат можно повторить и проверить позже.

**Масштабирование и изоляция окружений.** Сборки выполняются на агентах, а не на контроллере. В этой работе PHP установлен только в образе агента, а контроллер о нём вообще ничего не знает. Для проекта на другом языке достаточно добавить ещё один агент со своей меткой, а при большой нагрузке - несколько одинаковых агентов.

**Интеграции через плагины.** У Jenkins больше тысячи плагинов: Git и GitHub, Docker, Kubernetes, уведомления в почту и мессенджеры, отчёты о тестах и покрытии. В этой работе через плагины подключены git-репозиторий (Git), агент по SSH (SSH Build Agents) и хранение ключа (Credentials).

**Открытый исходный код и большое сообщество.** Jenkins бесплатен, его можно развернуть у себя (как здесь, в Docker), а на большинство ошибок уже есть ответы в документации и на форумах.

### Какие ещё типы агентов существуют

**Встроенный узел (Built-In Node).** Это сам контроллер. Подключать ничего не нужно, но сборка работает с теми же правами, что и сам Jenkins, и может испортить его настройки, поэтому документация Jenkins рекомендует установить у встроенного узла 0 исполнителей и использовать его только для небольших тестов.

**Постоянный SSH-агент (Permanent Agent, Launch agents via SSH).** Тип из этой работы, весь его запуск виден в журнале узла из шага 6: вход по ключу, копирование `remoting.jar` по sftp и старт `java -jar remoting.jar`. Подходит, когда агент - постоянно работающая машина или контейнер, до которого контроллер может достучаться по сети.

**Входящий агент (inbound agent).** На машине агента запускается `agent.jar` с адресом контроллера и секретом узла, который Jenkins показывает на странице узла. Готовый образ - `jenkins/inbound-agent`. Удобен, когда агент находится за NAT или межсетевым экраном и контроллер не может подключиться к нему сам, например агент на Windows-машине в другой сети.

**Docker-агенты.** Сборка запускается в одноразовом контейнере. Вариант в Jenkinsfile: `agent { docker { image 'composer:2.10' } }` (плагин Docker Pipeline), тогда PHP и Composer приходят из готового образа. Вариант в настройках: Docker cloud (плагин Docker), где Jenkins сам создаёт контейнер-агент под каждую сборку и удаляет его после. Каждая сборка получает чистое окружение, а версия PHP выбирается прямо в Jenkinsfile.

**Агенты в Kubernetes.** Плагин Kubernetes создаёт под (pod) на каждую сборку, внутри могут быть несколько контейнеров (например, PHP и база данных для тестов). Подходит для больших команд, где кластер уже есть и нужно много параллельных сборок.

**Облачные виртуальные машины.** Плагины для Amazon EC2, Azure VM, Google Compute Engine запускают виртуальную машину, когда в очереди появляются сборки, и останавливают её после простоя. Так платят только за время, когда агенты действительно нужны.

### Проблемы при настройке и их решение

**1. Порт 8080 занят.**

- Проблема: `docker compose up -d` не запустил контроллер:
  ```
  Bind for 0.0.0.0:8080 failed: port is already allocated
  ```
- Причина: порт 8080 хоста уже опубликован контейнером `php_apache` из лабораторной работы №2 (видно по `docker ps --filter "publish=8080"`).
- Решение: задание требует адрес `http://localhost:8080`, поэтому я не стал менять порт в `docker-compose.yml`, а на время работы остановил `php_apache` командой `docker stop php_apache`. После работы его можно снова запустить через `docker start php_apache`.

**2. Composer не устанавливает PHPUnit, если стоит только php-cli.**

- Проблема: с Dockerfile строго из задания (только `php-cli`) и Composer команда `composer install` завершилась ошибкой:
  ```
  Your requirements could not be resolved to an installable set of packages.

    Problem 1
      - Root composer.json requires phpunit/phpunit ^10.5 -> satisfiable by phpunit/phpunit[10.5.62, ..., 10.5.66].
      - phpunit/phpunit[10.5.62, ..., 10.5.66] require ext-dom * -> it is missing from your system. Install or enable PHP's dom extension.
  ```
- Причина: в Debian пакет `php-cli` содержит только базовые расширения. PHPUnit требует `dom`, `xml`, `xmlwriter`, `libxml` и `mbstring`, а они лежат в отдельных пакетах.
- Решение: добавил в Dockerfile пакеты `php-xml` (dom, xml, xmlwriter) и `php-mbstring`, а для распаковки архивов Composer - `unzip`. Флаг `--ignore-platform-req=ext-dom`, который предлагает Composer, не подходит: PHPUnit установился бы, но не смог бы работать.

**3. Агент с Java 17 не запускается.**

- Проблема: сначала в Dockerfile был образ `jenkins/ssh-agent:jdk17`. Я рассчитывал, что агенту нужна Java только для `remoting.jar`, и любой поддерживаемой версии хватит. SSH-подключение прошло, `remoting.jar` скопировался и запустился, но сразу после `channel started` узел отключился:
  ```
  java.lang.UnsupportedClassVersionError: hudson/slaves/SlaveComputer$SlaveVersion has been compiled by a more recent version of the Java Runtime (class file version 65.0), this version of the Java Runtime only recognizes class file versions up to 61.0
  ...
  Agent JVM has not reported exit code. Is it still running?
  Launch failed - cleaning up connection
  ```
- Причина: class file version 65 - это Java 21, а 61 - Java 17. Jenkins 2.580.1 собран под Java 21, и контроллер передаёт агенту свои классы, которые Java 17 загрузить не может. Значит, версия Java на агенте должна быть не ниже той, под которую собран контроллер.
- Решение: заменил базовый образ на `jenkins/ssh-agent:jdk21` (`openjdk version "21.0.12.1"`), пересобрал агент (`docker compose up -d --build`), заново вставил ключ хоста (проблема 4), и узел подключился: `Agent successfully connected and online`.

**4. Ключ хоста изменился после пересоздания агента.**

- Проблема: каждый раз, когда контейнер `ssh-agent` создавался заново (последний раз - при пересборке на `jdk21` из проблемы 3), узел переставал подключаться, и Jenkins каждые 15 секунд повторял:
  ```
  [SSH] WARNING: The SSH key for this host does not match the key required in the connection configuration. Connections will be denied until the host key matches the configuration key.
  Key exchange was not finished, connection is closed.
  SSH Connection failed with IOException: "Key exchange was not finished, connection is closed.", retrying in 15 seconds. There are 9 more retries left.
  ```
- Причина: ключи хоста `/etc/ssh/ssh_host_*` лежат в самом контейнере, а не в томе, и создаются при первом запуске. Новый контейнер - новые ключи. Стратегия «Manually provided key» сравнивает ключ с сохранённым в настройках узла и отказывает в подключении. То есть она сработала так, как и должна: для неё это выглядит как подмена сервера.
- Решение: снова выполнил `docker exec ssh-agent cat /etc/ssh/ssh_host_ed25519_key.pub`, вставил новый ключ в поле SSH Key узла, сохранил и нажал «Launch agent». Простой перезапуск (`docker compose restart`) ключи не меняет, новые ключи появляются только при пересоздании контейнера (`up` после изменений, `down` + `up`, `--build`).

## Выводы

1. С помощью Docker Compose я поднял стенд Jenkins из двух контейнеров: контроллер `jenkins/jenkins:lts` (Jenkins 2.580.1) и SSH-агент, собранный из своего Dockerfile. Файл `docker-compose.yml` полностью совпадает с заданием, добавлены только комментарии.
2. Агент подключён к контроллеру по SSH с ключевой парой: открытый ключ передаётся агенту через `.env`, закрытый хранится в учётных данных Jenkins и в git не попадает. Ключ хоста агента проверяется стратегией «Manually provided key», и я на практике увидел, как она блокирует подключение после смены ключа.
3. Образ агента должен соответствовать и проекту, и контроллеру: для PHPUnit нужны расширения `dom`, `xml`, `mbstring` сверх `php-cli`, а версия Java на агенте не может быть ниже, чем у контроллера (Java 17 не подошла, нужна Java 21).
4. Pipeline из SCM берёт Jenkinsfile из репозитория, выполняется на агенте с меткой `php-agent`, ставит зависимости через Composer по `composer.lock` и запускает 9 модульных тестов PHPUnit. Сборка №1 завершилась статусом `SUCCESS`, все тесты прошли.
5. Благодаря атрибутам `#[TestDox]` и ключу `--testdox` журнал сборки читается без исходного кода: по нему видно, какое поведение журнала оценок проверено.
6. Главное, что я понял: Jenkins сам по себе ничего не собирает. Он хранит описание процесса (Jenkinsfile), выбирает подходящий агент по метке и сохраняет результат. Вся работа выполняется на агентах, поэтому от правильной подготовки их окружения зависит, пройдёт сборка или нет.
