<?php

declare(strict_types=1);

namespace Bordeniuc\Gradebook;

/**
 * Разбор оценок, введённых текстом, в журнал GradeBook.
 *
 * Формат: одна строка на предмет, «Предмет: 8 9 10».
 * Оценки отделяются пробелами или запятыми, пустые строки пропускаются.
 * Так оценки вводятся на веб-странице журнала (public/index.php).
 */
final class GradeTextParser
{
    /**
     * Превращает текст в журнал оценок.
     *
     * @param string $text строки вида «Предмет: оценки»
     *
     * @throws GradeException если строка без двоеточия, без оценок,
     *                        с нечисловой оценкой или с оценкой вне шкалы
     */
    public function parse(string $text): GradeBook
    {
        $gradeBook = new GradeBook();

        // Разбиваем текст на строки; \R понимает и \n, и \r\n из формы браузера
        $lines = preg_split('/\R/u', $text) ?: [];

        foreach ($lines as $index => $line) {
            // Номер строки для сообщения об ошибке считается с единицы
            $lineNumber = $index + 1;

            // Пустые строки и строки из пробелов просто пропускаем
            if (trim($line) === '') {
                continue;
            }

            // Без двоеточия нельзя отделить название предмета от оценок
            if (!str_contains($line, ':')) {
                throw new GradeException(sprintf(
                    'Строка %d: нет двоеточия между предметом и оценками.',
                    $lineNumber,
                ));
            }

            // Делим только по первому двоеточию: остальная часть строки содержит оценки
            [$subject, $gradesText] = explode(':', $line, 2);

            // Оценки разделены пробелами и (или) запятыми
            $gradeTokens = preg_split('/[\s,]+/u', trim($gradesText), -1, PREG_SPLIT_NO_EMPTY) ?: [];

            if ($gradeTokens === []) {
                throw new GradeException(sprintf('Строка %d: нет ни одной оценки.', $lineNumber));
            }

            foreach ($gradeTokens as $token) {
                // Принимаем только целые числа: «8.5» или «отл» не являются оценками
                if (preg_match('/^\d+$/', $token) !== 1) {
                    throw new GradeException(sprintf(
                        'Строка %d: «%s» не является целой оценкой.',
                        $lineNumber,
                        $token,
                    ));
                }

                // Границы шкалы и пустое название проверяет сам журнал
                $gradeBook->addGrade($subject, (int) $token);
            }
        }

        return $gradeBook;
    }
}
