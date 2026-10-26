<?php

declare(strict_types=1);

namespace Bordeniuc\Gradebook;

/**
 * Исключение журнала оценок.
 *
 * Выбрасывается, когда в журнал пытаются записать неверные данные
 * (оценку вне шкалы 1-10, пустое название предмета) или запрашивают
 * средний балл по предмету, которого нет в журнале.
 */
final class GradeException extends \InvalidArgumentException
{
}
