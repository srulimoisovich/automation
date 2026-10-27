// Сборка и тестирование gradebook на SSH-агенте с PHP (узел ssh-agent1, метка php-agent).
pipeline {
    agent {
        label 'php-agent'
    }

    stages {
        stage('Клонирование репозитория') {
            steps {
                checkout scm
                sh 'git log -1 --format="%h %an %s"'
            }
        }

        stage('Установка зависимостей') {
            steps {
                sh '''
                    cd lab05/gradebook
                    php --version
                    composer install --no-interaction --optimize-autoloader
                '''
            }
        }

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
    }

    post {
        always {
            echo 'Pipeline completed.'
        }
        success {
            echo 'All stages completed successfully!'
        }
        failure {
            echo 'Errors detected in the pipeline.'
        }
    }
}
