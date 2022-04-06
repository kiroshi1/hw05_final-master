import datetime as dt


def year(request):
    """
    Добавляет переменную с текущим годом.
    """
    curr_year = dt.datetime.today().year
    return {'year': curr_year}
