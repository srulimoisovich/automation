// Настройка тестового сервера плейбуком setup_test_server.yml с управляющего узла Ansible.
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
