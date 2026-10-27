// Сборка и тестирование gradebook на SSH-агенте с PHP (узел ssh-agent1, метка php-agent).
// Задание Jenkins: Pipeline script from SCM, Script Path lab05/pipelines/php_build_and_test_pipeline.groovy.
pipeline {
    // Сборку выполняет любой узел с меткой php-agent; на нём установлены PHP и Composer
    agent {
        label 'php-agent'
    }

    stages {
        // Декларативный конвейер уже получил репозиторий перед первым этапом,
        // но задание перечисляет клонирование отдельным этапом, поэтому checkout scm повторён явно.
        // git log печатает коммит, который собирается: так в журнале сборки видна точная версия.
        stage('Клонирование репозитория') {
            steps {
                checkout scm
                sh 'git log -1 --format="%h %an %s"'
            }
        }

        // Зависимости ставятся строго по composer.lock; PHPUnit попадает в vendor/
        stage('Установка зависимостей') {
            steps {
                sh '''
                    cd lab05/gradebook
                    php --version
                    composer install --no-interaction --optimize-autoloader
                '''
            }
        }

        // --testdox печатает названия тестов из атрибутов TestDox,
        // --log-junit пишет отчёт в формате JUnit для Jenkins,
        // --testdox-html сохраняет тот же список тестов страницей HTML
        stage('Запуск тестов') {
            steps {
                sh '''
                    cd lab05/gradebook
                    vendor/bin/phpunit --testdox --log-junit build/junit.xml --testdox-html build/testdox.html
                '''
            }
        }

        // junit показывает результаты тестов на странице сборки (плагин JUnit),
        // archiveArtifacts сохраняет HTML-отчёт среди артефактов сборки
        stage('Отчёт о тестах') {
            steps {
                junit 'lab05/gradebook/build/junit.xml'
                archiveArtifacts artifacts: 'lab05/gradebook/build/testdox.html'
            }
        }
    }

    // Сообщения после завершения конвейера, как в шаблоне из lab04
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
