from datetime import datetime, timedelta, date
import sys

from mock import mock_open, patch, Mock
import pytest

from days_calc import (
    Item,
    RestartTotals,
    Start,
    Work,
    itemify,
    item_factory,
    WorkItem,
    initial_state,
    expect_work,
    working,
    ParserContext,
    parse_workstamps,
    filter_report,
    filter_customer,
    stats_by_day,
    WorkDay,
    WorkReport,
    format_timedelta,
    customer_totals,
    customer_summary,
    day_report,
    TextReport,
    cmdline_arguments)


@pytest.mark.parametrize(('attr', 'value'), [
    ('is_restart', False),
    ('is_start', False),
    ('is_work', False),
    ('lineno', 24)])
def test_item(attr, value):
    sut = Item(24)
    assert value == getattr(sut, attr)


class TestItem(object):
    @pytest.fixture
    def sut(self):
        return RestartTotals(24)

    @pytest.mark.parametrize(('attr', 'value'), [
        ('is_restart', True),
        ('is_start', False),
        ('is_work', False),
        ('lineno', 24)])
    def test_init(self, attr, value, sut):
        assert value == getattr(sut, attr)

    def test_repr(self, sut):
        assert 'line 24: restartotals' == repr(sut)

    @pytest.mark.parametrize(('other', 'expected'), [
        (RestartTotals(24), True),
        (RestartTotals(12), False)])
    def test_eq(self, sut, other, expected):
        assert expected == (sut == other)


class TestStart(object):
    @pytest.fixture
    def sut(self):
        return Start(12, '2001-02-03 15:34')

    @pytest.mark.parametrize(('attr', 'value'), [
        ('is_restart', False),
        ('is_start', True),
        ('is_work', False),
        ('lineno', 12),
        ('when', datetime(2001, 2, 3, 15, 34))])
    def test_init(self, attr, value, sut):
        assert value == getattr(sut, attr)

    def test_repr(self, sut):
        assert 'line 12: 2001-02-03 15:34 start' == repr(sut)

    @pytest.mark.parametrize(('other', 'expected'), [
        (Start(12, '2001-02-03 15:34'), True),
        (Start(21, '2001-02-03 15:34'), False),
        (Start(12, '2012-02-03 15:34'), False)])
    def test_eq(self, sut, other, expected):
        assert expected == (sut == other)


class TestWork(object):
    @pytest.fixture
    def sut(self):
        return Work(12, '2001-02-03 15:34', 'cust', 'desc')

    @pytest.mark.parametrize(('attr', 'value'), [
        ('is_restart', False),
        ('is_start', False),
        ('is_work', True),
        ('lineno', 12),
        ('when', datetime(2001, 2, 3, 15, 34)),
        ('customer', 'cust'),
        ('description', 'desc')])
    def test_init(self, attr, value, sut):
        assert value == getattr(sut, attr)

    def test_repr(self, sut):
        assert 'line 12: 2001-02-03 15:34 cust desc' == repr(sut)

    @pytest.mark.parametrize(('other', 'expected'), [
        (Work(12, '2001-02-03 15:34', 'cust', 'desc'), True),
        (Work(21, '2001-02-03 15:34', 'cust', 'desc'), False),
        (Work(12, '2021-02-03 15:34', 'cust', 'desc'), False),
        (Work(12, '2001-02-03 15:34', '21st', 'desc'), False),
        (Work(12, '2001-02-03 15:34', 'cust', '21sc'), False)])
    def test_eq(self, sut, other, expected):
        assert expected == (sut == other)


class TestItemify(object):
    def test_iter(self):
        m = mock_open()
        m.return_value.__iter__.return_value = ['  ', '2001-02-03 15:34 start']
        with patch('days_calc.open', m, create=True):
            result = list(itemify(''))
        assert [Start(1, '2001-02-03 15:34')] == result

    def test_open_right_file(self):
        m = mock_open()
        with patch('days_calc.open', m, create=True) as popen:
            result = list(itemify('filename'))
        popen.assert_called_with('filename', 'r')


class TestItemFactory(object):
    def test_restart(self):
        assert RestartTotals(12) == item_factory(12, 'restarttotals')

    def test_start(self):
        res = item_factory(12, '2001-02-03 15:34 start')
        assert Start(12, '2001-02-03 15:34') == res

    def test_work(self):
        res = item_factory(12, '2001-02-03 15:34 customer my descrip tion')
        expected = Work(12, '2001-02-03 15:34', 'customer', 'my descrip tion')
        assert expected == res


@pytest.fixture
def work_line():
    return Work(12, '2001-01-03 04:15', 'cst', 'dsc')


@pytest.fixture
def start_line():
    return Start(11, '2001-01-02 03:00')


@pytest.fixture
def restart_line():
    return RestartTotals(13)


class TestWorkItem(object):
    @pytest.fixture
    def sut(self, work_line):
        return WorkItem(datetime(2001, 1, 2, 3, 0, 0), work_line)

    @pytest.mark.parametrize(('attr', 'expected'), [
        ('start', datetime(2001, 1, 2, 3, 0, 0)),
        ('end', datetime(2001, 1, 3, 4, 15, 0)),
        ('customer', 'cst'),
        ('description', 'dsc'),
        ('duration', timedelta(1, 3600 + (60 * 15))),
        ('date', date(2001, 1, 3))])
    def test_init(self, attr, expected, sut):
        assert expected == getattr(sut, attr)

    @pytest.mark.parametrize(('other', 'expected'), [
        (WorkItem(datetime(2001, 1, 2, 3), work_line()), True),
        (WorkItem('other', work_line()), False),
        (WorkItem(datetime(2001, 1, 2, 3),
         Work(12, '9999-01-03 04:15', 'cst', 'dsc')), False),
        (WorkItem(datetime(2001, 1, 2, 3),
         Work(12, '2001-01-03 04:15', 'lol', 'dsc')), False),
        (WorkItem(datetime(2001, 1, 2, 3),
         Work(12, '2001-01-03 04:15', 'cst', 'lol')), False)])
    def test_eq(self, sut, other, expected):
        assert expected == (sut == other)


class TestInitialState(object):
    def test_no_start_line(self, work_line):
        with pytest.raises(RuntimeError):
            initial_state('context', work_line)

    def test_start_period(self, start_line):
        context = Mock()
        initial_state(context, start_line)
        assert start_line.when == context.start_period

    def test_next_state(self, start_line):
        assert expect_work is initial_state(Mock(), start_line)


class TestExpectWork(object):
    def test_no_work_line(self, start_line):
        with pytest.raises(RuntimeError):
            expect_work('context', start_line)

    def test_add_item(self, work_line):
        context = Mock()
        expect_work(context, work_line)
        context.add_item.assert_called_with(work_line)

    def test_next_state(self, work_line):
        assert working is expect_work(Mock(), work_line)


class TestWorking(object):
    def test_start_next(self, start_line):
        assert expect_work is working(Mock(), start_line)

    def test_start_change_period(self, start_line):
        context = Mock()
        working(context, start_line)
        assert start_line.when == context.start_period

    def test_work_next(self, work_line):
        assert working is working(Mock(), work_line)

    def test_work_add_item(self, work_line):
        context = Mock()
        working(context, work_line)
        context.add_item.assert_called_with(work_line)

    def test_restart_next(self, restart_line):
        assert initial_state is working(Mock(), restart_line)

    def test_restart_report(self, restart_line):
        context = Mock()
        working(context, restart_line)
        context.add_current_report.assert_called_with()

    def test_error(self):
        with pytest.raises(RuntimeError):
            working('context', Item(12))


class TestParserContext(object):
    @pytest.fixture
    def sut(self):
        return ParserContext()

    def test_init_start_period(self, sut):
        assert sut.start_period is None

    def test_add_item(self, sut, work_line):
        sut.add_item(work_line)

        sut.add_current_report()
        assert [[WorkItem(None, work_line)]] == sut.reports

    def test_add_item_update_start(self, sut, work_line):
        sut.add_item(work_line)
        assert sut.start_period == work_line.when

    def test_add_current_report_empty(self, sut):
        sut.add_current_report()
        assert [] == sut.reports

    def test_add_current_report_start(self, sut, work_line):
        sut.start_period = 'banana'
        sut.add_item(work_line)
        sut.add_current_report()
        assert sut.start_period is None


@pytest.fixture
def work_items():
    return [
        WorkItem(datetime(2001, 1, 1),
                 Work(13, '2001-01-01 01:00', 'mycust', 'mydesc')),
        WorkItem(datetime(2001, 1, 2),
                 Work(16, '2001-01-02 01:00', 'mycust', 'mydesc'))]


class TestParseWorkstamps(object):
    def call_sut(self, items):
        with patch('days_calc.itemify') as pitemify:
            pitemify.return_value = items
            return parse_workstamps('filename'), pitemify

    @pytest.fixture
    def items(self):
        return [
            Start(12, '2001-01-01 00:00'),
            Work(13, '2001-01-01 01:00', 'mycust', 'mydesc'),
            RestartTotals(14),
            Start(15, '2001-01-02 00:00'),
            Work(16, '2001-01-02 01:00', 'mycust', 'mydesc')]

    def test_build_itemify(self):
        res, pitemify = self.call_sut([])
        pitemify.assert_called_with('filename')

    def test_parse(self, items, work_items):
        res = self.call_sut(items)[0]
        expected = [[work_items[0]], [work_items[1]]]
        assert expected == res


class TestFilterReport(object):
    def test_none(self):
        assert 'items' == filter_report(None, 'items')

    def test_report(self):
        assert (3,) == filter_report(0, [1, 2, 3])


class TestFilterCustomer(object):
    def test_none(self):
        assert 'items' == filter_customer(None, 'items')

    def test_filter(self):
        myitem = Mock(customer='a')
        items = [
            [myitem, Mock(customer='b')],
            [Mock(customer='b'), Mock(customer='b')]]
        assert [[myitem]] == filter_customer('a', items)


class TestStatsByDay(object):
    @pytest.fixture
    def items(self, work_items):
        return [work_items]

    def test_grouping(self, items):
        assert [[[items[0][0]], [items[0][1]]]] == stats_by_day(items)

    def test_day_stats(self, items):
        assert isinstance(stats_by_day(items)[0][0], WorkDay)

    def test_report_stats(self, items):
        assert isinstance(stats_by_day(items)[0], WorkReport)


@pytest.fixture
def work_day(work_items):
    return WorkDay(work_items)


class TestWorkDay(object):
    def test_items(self, work_items, work_day):
        assert work_items == list(work_day)

    def test_customer_day_totals(self, work_day):
        assert {'mycust': timedelta(0, 7200)} == work_day.customers

    def test_date(self, work_day, work_items):
        assert work_items[0].date == work_day.date


@pytest.fixture
def work_report(work_day):
    return WorkReport([work_day, work_day])


class TestWorkReport(object):
    def test_items(self, work_report, work_day):
        assert [work_day, work_day] == list(work_report)

    def test_totals(self, work_report):
        assert {'mycust': timedelta(0, 14400)} == work_report.customers


class TestFormatTimestamp(object):
    def test_format(self):
        assert '240:05' == format_timedelta(timedelta(10, 300))

    def test_withseconds(self):
        with pytest.raises(AssertionError):
            format_timedelta(timedelta(0, 1))


class TestCustomerTotals(object):
    def test_no_prefix(self):
        res = customer_totals({'c1': timedelta(1)})
        assert ['c1: 24:00'] == res

    def test_prefix(self):
        res = customer_totals({'c1': timedelta(1)}, 'hey: ')
        assert ['hey: c1: 24:00'] == res


def test_report_summary():
    res = customer_summary({'mycust': timedelta(0, 7200)})
    expected = [
        '---------------------------------------------',
        'restart totals: mycust: 2:00', '']
    assert expected == res


def test_day_report(work_day):
    res = day_report(work_day)
    expected = [
        '---------- 2001-01-01 ----------',
        '1:00 mycust mydesc',
        '1:00 mycust mydesc',
        'mycust: 2:00']
    assert res == expected


class TestTextReport(object):
    @pytest.fixture
    def sut(self, work_report):
        return TextReport([work_report])

    def test_lines(self, sut):
        lines = [
            '---------- 2001-01-01 ----------', '1:00 mycust mydesc',
            '1:00 mycust mydesc', 'mycust: 2:00',
            '---------- 2001-01-01 ----------', '1:00 mycust mydesc',
            '1:00 mycust mydesc', 'mycust: 2:00',
            '---------------------------------------------',
            'restart totals: mycust: 4:00', '']
        # 4 = 1 + 2 + 1 lines day summary x 2, 3 lines for report summary
        assert sut.lines

    def test_text(self, sut):
        text = """---------- 2001-01-01 ----------
1:00 mycust mydesc
1:00 mycust mydesc
mycust: 2:00
---------- 2001-01-01 ----------
1:00 mycust mydesc
1:00 mycust mydesc
mycust: 2:00
---------------------------------------------
restart totals: mycust: 4:00
"""
        assert text == sut.text


class TestCmdlineArguments(object):
    def run_sut(self, arguments):
        args = ['basename'] + arguments
        with patch.object(sys, 'argv', args),\
                patch('days_calc.expanduser') as pexpand:
            pexpand.return_value = 'user_folder!'
            return cmdline_arguments()

    def test_empty(self):
        args = self.run_sut([])
        expected = dict(
            customer=None, file='user_folder!', week=None)
        assert expected == vars(args)

    def test_week(self):
        args = self.run_sut(['2'])
        expected = dict(customer=None, file='user_folder!', week=2)
        assert expected == vars(args)

    def test_customer(self):
        args = self.run_sut(['--customer', 'cust'])
        expected = dict(customer='cust', file='user_folder!', week=None)
        assert expected == vars(args)

    def test_file(self):
        args = self.run_sut(['--file', 'myfile'])
        expected = dict(customer=None, file='myfile', week=None)
        assert expected == vars(args)
