// Выкладка gradebook на тестовый сервер с помощью Ansible.
pipeline {
    agent {
        label 'ansible-control'
    }

    stages {
        stage('Клонирование репозитория') {
            steps {
                checkout scm
                sh 'git log -1 --format="%h %an %s"'
            }
        }

        stage('Копирование файлов на сервер') {
            steps {
                sh 'tar -czf lab05/gradebook.tar.gz -C lab05/gradebook src public'
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
