// Выкладка gradebook на тестовый сервер с помощью Ansible.
// Задание Jenkins: Pipeline script from SCM, Script Path lab05/pipelines/php_deploy_pipeline.groovy.
// Перед первой выкладкой сервер должен быть настроен конвейером ansible_setup_pipeline.groovy.
pipeline {
    // Выкладку выполняет управляющий узел Ansible
    agent {
        label 'ansible-control'
    }

    stages {
        // Явное клонирование репозитория с проектом
        stage('Клонирование репозитория') {
            steps {
                checkout scm
                sh 'git log -1 --format="%h %an %s"'
            }
        }

        stage('Копирование файлов на сервер') {
            steps {
                // В архив попадают только src/ и public/: тесты, phpunit.xml и Composer
                // на сервере не нужны, а внешних зависимостей во время работы у проекта нет.
                sh 'tar -czf lab05/gradebook.tar.gz -C lab05/gradebook src public'
                // Ключ для входа на сервер передаётся так же, как в конвейере настройки
                sshagent(credentials: ['test_server_ansible_key']) {
                    sh '''
                        cd lab05/ansible
                        mkdir -p ~/.ssh
                        ssh-keyscan -t ed25519 test-server > ~/.ssh/known_hosts
                        ansible-playbook -i hosts.ini deploy_gradebook.yml
                    '''
                }
            }
        }

        stage('Настройка проекта на сервере') {
            steps {
                sshagent(credentials: ['test_server_ansible_key']) {
                    // Строка в одинарных кавычках: $BUILD_NUMBER подставляет оболочка sh
                    // из переменной окружения сборки, а не Groovy
                    sh '''
                        cd lab05/ansible
                        ansible-playbook -i hosts.ini configure_gradebook.yml -e build_number=$BUILD_NUMBER
                    '''
                }
            }
        }
    }

    post {
        success {
            echo 'Журнал оценок выложен на тестовый сервер.'
        }
        failure {
            echo 'Выкладка завершилась ошибкой.'
        }
    }
}
