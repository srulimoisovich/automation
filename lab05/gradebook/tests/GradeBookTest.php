<?php

declare(strict_types=1);

namespace Bordeniuc\Gradebook\Tests;

use Bordeniuc\Gradebook\GradeBook;
use Bordeniuc\Gradebook\GradeException;
use PHPUnit\Framework\Attributes\TestDox;
use PHPUnit\Framework\TestCase;

/**
 * Модульные тесты журнала оценок GradeBook.
 *
 * Атрибут TestDox задаёт название теста в виде предложения:
 * с ключом --testdox PHPUnit печатает именно его.
 */
final class GradeBookTest extends TestCase
{
    /** Журнал, который каждый тест получает пустым. */
    private GradeBook $gradeBook;

    /**
     * Создаёт новый пустой журнал перед каждым тестом.
     */
    protected function setUp(): void
    {
        $this->gradeBook = new GradeBook();
    }

    /** Добавленная оценка появляется в журнале вместе с предметом. */
    #[TestDox('Оценка добавляется к предмету')]
    public function testGradeIsAddedToSubject(): void
    {
        $this->gradeBook->addGrade('Математика', 9);

        $this->assertSame(['Математика'], $this->gradeBook->subjects());
        $this->assertSame(9.0, $this->gradeBook->averageFor('Математика'));
    }

    /** Среднее (8 + 9 + 9) / 3 = 8.666... округляется до 8.67. */
    #[TestDox('Средний балл по предмету округляется до двух знаков')]
    public function testSubjectAverageIsRoundedToTwoDecimals(): void
    {
        $this->gradeBook->addGrade('Физика', 8);
        $this->gradeBook->addGrade('Физика', 9);
        $this->gradeBook->addGrade('Физика', 9);

        $this->assertSame(8.67, $this->gradeBook->averageFor('Физика'));
    }

    /** Общий балл равен среднему средних: (10 + 7) / 2 = 8.5, а не среднее всех трёх оценок. */
    #[TestDox('Общий средний балл считается по средним баллам предметов')]
    public function testOverallAverageUsesSubjectAverages(): void
    {
        $this->gradeBook->addGrade('Информатика', 10);
        $this->gradeBook->addGrade('История', 6);
        $this->gradeBook->addGrade('История', 8);

        $this->assertSame(8.5, $this->gradeBook->overallAverage());
    }

    /** Оценка ниже нижней границы шкалы отклоняется. */
    #[TestDox('Оценка 0 не принимается')]
    public function testGradeZeroIsRejected(): void
    {
        $this->expectException(GradeException::class);

        $this->gradeBook->addGrade('Математика', 0);
    }

    /** Оценка выше верхней границы шкалы отклоняется. */
    #[TestDox('Оценка 11 не принимается')]
    public function testGradeElevenIsRejected(): void
    {
        $this->expectException(GradeException::class);

        $this->gradeBook->addGrade('Математика', 11);
    }

    /** Название из одних пробелов после trim становится пустым и отклоняется. */
    #[TestDox('Пустое название предмета не принимается')]
    public function testEmptySubjectIsRejected(): void
    {
        $this->expectException(GradeException::class);

        $this->gradeBook->addGrade('   ', 7);
    }

    /** Нельзя посчитать средний балл по предмету без оценок. */
    #[TestDox('Средний балл по неизвестному предмету вызывает исключение')]
    public function testAverageForUnknownSubjectThrows(): void
    {
        $this->expectException(GradeException::class);

        $this->gradeBook->averageFor('Химия');
    }

    /** Средний балл 4.5 означает задолженность, ровно 5 уже нет. */
    #[TestDox('Предметы со средним баллом ниже 5 считаются задолженностями')]
    public function testSubjectsBelowFiveAreFailed(): void
    {
        $this->gradeBook->addGrade('Химия', 4);
        $this->gradeBook->addGrade('Химия', 5);
        $this->gradeBook->addGrade('Биология', 5);
        $this->gradeBook->addGrade('География', 9);

        $this->assertSame(['Химия'], $this->gradeBook->failedSubjects());
    }

    /** В журнале без оценок общий средний балл равен нулю. */
    #[TestDox('У пустого журнала средний балл равен 0')]
    public function testEmptyGradeBookHasZeroAverage(): void
    {
        $this->assertSame(0.0, $this->gradeBook->overallAverage());
    }
}
