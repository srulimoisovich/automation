<?php

declare(strict_types=1);

namespace Bordeniuc\Gradebook;

/**
 * Электронный журнал оценок одного студента.
 *
 * Оценки ставятся по 10-балльной шкале, принятой в Молдове:
 * от 1 до 10, где 5 - минимальная положительная оценка.
 * Журнал хранит оценки по предметам и считает средние баллы.
 */
final class GradeBook
{
    /** Минимальная оценка шкалы. */
    public const MIN_GRADE = 1;

    /** Максимальная оценка шкалы. */
    public const MAX_GRADE = 10;

    /** Средний балл, начиная с которого предмет считается сданным. */
    public const PASSING_AVERAGE = 5.0;

    /**
     * Оценки, сгруппированные по предметам.
     *
     * @var array<string, list<int>> ключ - название предмета, значение - список оценок
     */
    private array $gradesBySubject = [];

    /**
     * Добавляет оценку по предмету.
     *
     * Пробелы по краям названия предмета отбрасываются.
     *
     * @param string $subject название предмета
     * @param int    $grade   оценка от 1 до 10
     *
     * @throws GradeException если название пустое или оценка вне шкалы
     */
    public function addGrade(string $subject, int $grade): void
    {
        // Убираем пробелы по краям, чтобы " Математика " и "Математика" были одним предметом
        $subjectName = trim($subject);

        // Пустое название предмета не имеет смысла
        if ($subjectName === '') {
            throw new GradeException('Название предмета не может быть пустым.');
        }

        // Оценка должна попадать в 10-балльную шкалу
        if ($grade < self::MIN_GRADE || $grade > self::MAX_GRADE) {
            throw new GradeException(sprintf(
                'Оценка %d вне шкалы: допустимы значения от %d до %d.',
                $grade,
                self::MIN_GRADE,
                self::MAX_GRADE,
            ));
        }

        // Дописываем оценку в список предмета (список создаётся автоматически)
        $this->gradesBySubject[$subjectName][] = $grade;
    }

    /**
     * Возвращает названия предметов в порядке добавления первой оценки.
     *
     * @return list<string>
     */
    public function subjects(): array
    {
        return array_keys($this->gradesBySubject);
    }

    /**
     * Возвращает оценки по предмету в порядке добавления.
     *
     * Нужен веб-странице, чтобы показать в таблице сами оценки рядом со средним баллом.
     *
     * @param string $subject название предмета
     *
     * @return list<int>
     *
     * @throws GradeException если предмета нет в журнале
     */
    public function gradesFor(string $subject): array
    {
        $subjectName = trim($subject);

        // Как и в averageFor, неизвестный предмет считается ошибкой
        if (!isset($this->gradesBySubject[$subjectName])) {
            throw new GradeException(sprintf('Предмет "%s" отсутствует в журнале.', $subjectName));
        }

        return $this->gradesBySubject[$subjectName];
    }

    /**
     * Возвращает средний балл по предмету, округлённый до двух знаков.
     *
     * @param string $subject название предмета
     *
     * @throws GradeException если по предмету нет ни одной оценки
     */
    public function averageFor(string $subject): float
    {
        $subjectName = trim($subject);

        // Без оценок средний балл посчитать нельзя
        if (!isset($this->gradesBySubject[$subjectName])) {
            throw new GradeException(sprintf('Предмет "%s" отсутствует в журнале.', $subjectName));
        }

        $grades = $this->gradesBySubject[$subjectName];

        return round(array_sum($grades) / count($grades), 2);
    }

    /**
     * Возвращает общий средний балл: среднее значение средних баллов по предметам.
     *
     * Каждый предмет весит одинаково, сколько бы оценок по нему ни было.
     * Для пустого журнала возвращается 0.0.
     */
    public function overallAverage(): float
    {
        // В пустом журнале нет предметов, делить не на что
        if ($this->gradesBySubject === []) {
            return 0.0;
        }

        // Собираем средний балл каждого предмета
        $averages = array_map(
            fn (string $subjectName): float => $this->averageFor($subjectName),
            $this->subjects(),
        );

        return round(array_sum($averages) / count($averages), 2);
    }

    /**
     * Возвращает предметы-задолженности: средний балл по ним ниже 5.
     *
     * @return list<string>
     */
    public function failedSubjects(): array
    {
        // Оставляем только предметы, средний балл которых меньше проходного
        $failed = array_filter(
            $this->subjects(),
            fn (string $subjectName): bool => $this->averageFor($subjectName) < self::PASSING_AVERAGE,
        );

        // array_filter сохраняет ключи, поэтому переиндексируем список
        return array_values($failed);
    }
}
