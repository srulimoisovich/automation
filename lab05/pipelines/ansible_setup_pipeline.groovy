// Настройка тестового сервера плейбуком setup_test_server.yml с управляющего узла Ansible.
// Задание Jenkins: Pipeline script from SCM, Script Path lab05/pipelines/ansible_setup_pipeline.groovy.
pipeline {
    // Узел ansible-control-node (контейнер ansible-agent), на нём установлен ansible-core
    agent {
        label 'ansible-control'
    }

    stages {
        // Явное клонирование репозитория с плейбуком (см. комментарий в php_build_and_test_pipeline.groovy)
        stage('Клонирование репозитория') {
            steps {
                checkout scm
                sh 'git log -1 --format="%h %an %s"'
            }
        }

        stage('Настройка тестового сервера') {
            steps {
                // Шаг sshagent (плагин SSH Agent) запускает программу ssh-agent и добавляет в неё
                // закрытый ключ из учётных данных test_server_ansible_key. Ключ живёт только в памяти
                // на время блока, на диск агента он не записывается; ssh внутри Ansible берёт его оттуда.
                sshagent(credentials: ['test_server_ansible_key']) {
                    // ssh-keyscan записывает ключ хоста test-server в known_hosts перед каждым запуском,
                    // поэтому проверка ключа хоста в Ansible остаётся включённой.
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
    }

    post {
        success {
            echo 'Тестовый сервер настроен.'
        }
        failure {
            echo 'Настройка тестового сервера завершилась ошибкой.'
        }
    }
}
