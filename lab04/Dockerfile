# Образ SSH-агента для Jenkins: Java 21, PHP и Composer
FROM jenkins/ssh-agent:jdk21

RUN apt-get update && apt-get install -y php-cli php-xml php-mbstring unzip && rm -rf /var/lib/apt/lists/*

ADD https://getcomposer.org/download/2.10.3/composer.phar /usr/local/bin/composer
RUN chmod 755 /usr/local/bin/composer
