<?php

declare(strict_types=1);

namespace Bordeniuc\Gradebook\Tests;

use Bordeniuc\Gradebook\GradeException;
use Bordeniuc\Gradebook\GradeTextParser;
use PHPUnit\Framework\Attributes\TestDox;
use PHPUnit\Framework\TestCase;

/**
 * Модульные тесты разбора текста с оценками GradeTextParser.
 */
final class GradeTextParserTest extends TestCase
{
    /** Две строки дают два предмета; запятые и пробелы одинаково разделяют оценки. */
    #[TestDox('Правильный текст превращается в журнал с предметами и оценками')]
    public function testValidTextBecomesGradeBook(): void
    {
        $gradeBook = (new GradeTextParser())->parse("Математика: 8 9 10\nФизика: 4, 5,3");

        $this->assertSame(['Математика', 'Физика'], $gradeBook->subjects());
        $this->assertSame(9.0, $gradeBook->averageFor('Математика'));
        $this->assertSame([4, 5, 3], $gradeBook->gradesFor('Физика'));
        $this->assertSame(4.0, $gradeBook->averageFor('Физика'));
    }

    /** Строка без двоеточия отклоняется, а в сообщении указан её номер. */
    #[TestDox('Строка без двоеточия вызывает исключение с номером строки')]
    public function testLineWithoutColonIsRejected(): void
    {
        $this->expectException(GradeException::class);
        $this->expectExceptionMessage('Строка 2');

        (new GradeTextParser())->parse("Математика: 8\nФизика 7");
    }

    /** Пустые строки и строки из пробелов не считаются ошибкой. */
    #[TestDox('Пустые строки пропускаются')]
    public function testEmptyLinesAreSkipped(): void
    {
        $gradeBook = (new GradeTextParser())->parse("\nИстория: 7\n   \n\r\nХимия: 6\n");

        $this->assertSame(['История', 'Химия'], $gradeBook->subjects());
    }
}
