from datetime import datetime

from mock import mock_open, patch
import pytest

from days_calc import (
    Item,
    RestartTotals,
    Start,
    Work,
    Itemify,
    item_factory)


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
            result = list(Itemify(''))
        assert [Start(1, '2001-02-03 15:34')] == result

    def test_open_right_file(self):
        m = mock_open()
        with patch('days_calc.open', m, create=True) as popen:
            result = list(Itemify('filename'))
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
