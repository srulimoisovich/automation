<?php

declare(strict_types=1);

/*
 * Веб-страница журнала оценок: форма с текстом оценок и таблица средних баллов.
 *
 * На тестовый сервер выкладываются только src/ и public/, без vendor/ и Composer.
 * У библиотеки нет зависимостей во время работы, поэтому вместо автозагрузчика
 * Composer используется короткий собственный: он отображает пространство имён
 * Bordeniuc\Gradebook\ на каталог ../src/ так же, как PSR-4 в composer.json.
 */
spl_autoload_register(static function (string $className): void {
    $prefix = 'Bordeniuc\\Gradebook\\';

    // Чужие классы этот автозагрузчик не трогает
    if (!str_starts_with($className, $prefix)) {
        return;
    }

    // Bordeniuc\Gradebook\GradeBook -> ../src/GradeBook.php
    $relativeName = substr($className, strlen($prefix));
    require __DIR__ . '/../src/' . str_replace('\\', '/', $relativeName) . '.php';
});

use Bordeniuc\Gradebook\GradeBook;
use Bordeniuc\Gradebook\GradeException;
use Bordeniuc\Gradebook\GradeTextParser;

// Настройки из config.php создаёт Ansible при выкладке (configure_gradebook.yml).
// Если страницу открыли без выкладки (например, локально), берутся значения по умолчанию.
$defaults = ['title' => 'Журнал оценок', 'build' => 'нет', 'deployed_at' => '', 'server' => 'локально'];
$configFile = __DIR__ . '/../config.php';
$config = is_file($configFile) ? array_merge($defaults, require $configFile) : $defaults;

// Время выкладки хранится в UTC; показываем его в часовом поясе из php.ini
$deployedAt = 'неизвестно когда';
if ($config['deployed_at'] !== '') {
    $deployedAt = (new DateTimeImmutable($config['deployed_at']))
        ->setTimezone(new DateTimeZone(date_default_timezone_get()))
        ->format('d.m.Y H:i');
}

// Пример, который стоит в форме при первом открытии страницы
$exampleText = "Математика: 8 9 10\nФизика: 4 5 3\nИстория: 7, 6, 9";
$gradesText = isset($_POST['grades']) ? (string) $_POST['grades'] : $exampleText;

$gradeBook = null;
$errorMessage = null;

// Таблицу считаем только после отправки формы
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    try {
        $gradeBook = (new GradeTextParser())->parse($gradesText);
    } catch (GradeException $exception) {
        $errorMessage = $exception->getMessage();
    }
}

// Средние баллы с десятичной запятой, как принято в Молдове (локаль ro_MD из ICU)
$numberFormatter = new NumberFormatter('ro_MD', NumberFormatter::DECIMAL);
$numberFormatter->setAttribute(NumberFormatter::MIN_FRACTION_DIGITS, 2);
$numberFormatter->setAttribute(NumberFormatter::MAX_FRACTION_DIGITS, 2);

/** Экранирует текст для вывода в HTML. */
function e(string $text): string
{
    return htmlspecialchars($text, ENT_QUOTES, 'UTF-8');
}
?>
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title><?= e($config['title']) ?></title>
    <style>
        body { font-family: Georgia, serif; max-width: 720px; margin: 24px auto 40px; padding: 0 12px; color: #222; }
        textarea { width: 100%; font: inherit; }
        table { border-spacing: 0; border-top: 2px solid #555; margin: 20px 0 8px; }
        th { text-align: left; }
        th, td { border-bottom: 1px solid #bbb; padding: 5px 14px 5px 4px; vertical-align: top; }
        caption { font-style: italic; text-align: left; margin-bottom: 0.4rem; }
        tr.failed { background: #fbe3e3; }
        tfoot td { font-weight: bold; }
        .error { color: #a00; }
        footer { margin-top: 2rem; font-size: 0.85rem; color: #666; }
    </style>
</head>
<body>
<h1><?= e($config['title']) ?></h1>

<p>Введите оценки: одна строка на предмет, например «Математика: 8 9 10».</p>

<?php if ($errorMessage !== null): ?>
    <p class="error">Ошибка: <?= e($errorMessage) ?></p>
<?php endif; ?>

<form method="post">
    <textarea name="grades" rows="6"><?= e($gradesText) ?></textarea>
    <p><button type="submit">Посчитать средние баллы</button></p>
</form>

<?php if ($gradeBook instanceof GradeBook): ?>
    <table>
        <caption>
            Шкала от <?= GradeBook::MIN_GRADE ?> до <?= GradeBook::MAX_GRADE ?>,
            предмет сдан при среднем балле от <?= e($numberFormatter->format(GradeBook::PASSING_AVERAGE)) ?>.
        </caption>
        <thead>
        <tr><th>Предмет</th><th>Оценки</th><th>Средний балл</th><th>Итог</th></tr>
        </thead>
        <tbody>
        <?php foreach ($gradeBook->subjects() as $subject): ?>
            <?php $isFailed = in_array($subject, $gradeBook->failedSubjects(), true); ?>
            <tr<?= $isFailed ? ' class="failed"' : '' ?>>
                <td><?= e($subject) ?></td>
                <td><?= e(implode(', ', $gradeBook->gradesFor($subject))) ?></td>
                <td><?= e($numberFormatter->format($gradeBook->averageFor($subject))) ?></td>
                <td><?= $isFailed ? 'не сдан' : 'сдан' ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
        <tfoot>
        <tr><td colspan="2">Общий средний балл</td><td colspan="2"><?= e($numberFormatter->format($gradeBook->overallAverage())) ?></td></tr>
        </tfoot>
    </table>
<?php endif; ?>

<footer>
    Сборка №<?= e((string) $config['build']) ?>, развёрнута <?= e($deployedAt) ?>, сервер <?= e($config['server']) ?>
</footer>
</body>
</html>
