#!/usr/bin/env python
"""
.workstamps report formatter
"""
from __future__ import print_function
from argparse import ArgumentParser
from datetime import datetime
from os.path import expanduser


##############################################################################
# Code related to splitting the .workstamps.txt file into tokens with
# information: start, restart totals and work items
##############################################################################
class Item(object):
    """Generic processing item for parsing .workstamps file"""
    is_restart = False
    is_start = False
    is_work = False

    def __init__(self, lineno):
        self.lineno = lineno

    def __eq__(self, other):
        return other.lineno == self.lineno and \
            other.is_restart == self.is_restart and \
            other.is_start == self.is_start and \
            other.is_work == self.is_work


class RestartTotals(Item):
    """Restart Totals Item in .workstamps file"""
    is_restart = True

    def __repr__(self):
        """Debugging helper representation"""
        return 'line {0}: restartotals'.format(self.lineno)


class Start(Item):
    """Start work item in .workstamps file"""
    is_start = True

    def __init__(self, lineno, date_time):
        super(Start, self).__init__(lineno)
        # Known format: year-month-day hour:minutes
        self.when = datetime(
            int(date_time[:4]),
            int(date_time[5:7]),
            int(date_time[8:10]),
            int(date_time[11:13]),
            int(date_time[14:16]))

    def __repr__(self):
        """Debugging helper representation"""
        return 'line {0}: {1:%Y-%m-%d %H:%M} start'.format(
            self.lineno, self.when)

    def __eq__(self, other):
        return other.when == self.when and \
            super(Start, self).__eq__(other)


class Work(Start):
    """Work item in .workstamps file"""
    is_start = False
    is_work = True

    def __init__(self, lineno, date_time, customer, description=''):
        super(Work, self).__init__(lineno, date_time)
        self.customer = customer
        self.description = description

    def __repr__(self):
        """Debugging helper representation"""
        return 'line {0}: {1:%Y-%m-%d %H:%M} {2} {3}'.format(
            self.lineno, self.when, self.customer, self.description)

    def __eq__(self, other):
        return other.customer == self.customer and \
            other.description == self.description and \
            super(Work, self).__eq__(other)


def itemify(filename):
    """Split a .workstamp file into items"""
    with open(filename, 'r') as infile:
        lineno = 0
        for line in infile:
            line = line.strip()
            if line:
                yield item_factory(lineno, line)
            lineno += 1


def item_factory(lineno, line):
    """Build the right item from a .workstamp line"""
    if line == 'restarttotals':
        return RestartTotals(lineno)
    date_time = line[:16]
    info = line[17:]
    if info == 'start':
        return Start(lineno, date_time)
    return Work(lineno, date_time, *info.split(' ', 1))


##############################################################################
# Understanding those items and bulding WorkItems with duration and grouping
# them using the restarttotal items
##############################################################################
class WorkItem(object):
    """Stores work item data using line items"""
    def __init__(self, start, line):
        self.start = start
        self.end = line.when
        self.customer = line.customer
        self.description = line.description

    @property
    def duration(self):
        """Work duration"""
        return self.end - self.start

    @property
    def date(self):
        """Work date based on the end date"""
        return self.end.date()

    def __eq__(self, other):
        return other.start == self.start and \
            other.end == self.end and \
            other.customer == self.customer and \
            other.description == self.description


def initial_state(context, item):
    """Initial state for the parser"""
    if not item.is_start:
        raise RuntimeError('first line should be a start', item)
    context.start_period = item.when
    return expect_work


def expect_work(context, item):
    """Expecting work items state"""
    if not item.is_work:
        raise RuntimeError('start must be followed by some activity', item)
    context.add_item(item)
    return working


def working(context, item):
    """Working state"""
    if item.is_start:
        return initial_state(context, item)
    elif item.is_work:
        return expect_work(context, item)
    elif item.is_restart:
        context.add_current_report()
        return initial_state
    raise RuntimeError('This shouldnt happen %s' % item)


class ParserContext(object):
    """Holds parsing context during parsing"""
    def __init__(self):
        self.__stack = []
        self.__reports = []
        self.start_period = None

    def add_current_report(self):
        """Adds the current work items as a group and start a new work item
        list"""
        if not self.__stack:
            return
        self.__reports.append(self.__stack)
        self.__stack = []
        self.start_period = None

    def add_item(self, line_item):
        """Adds a processed work item"""
        item = WorkItem(self.start_period, line_item)
        self.__stack.append(item)
        self.start_period = item.end

    @property
    def reports(self):
        """Reports stored during parsing"""
        return self.__reports


def parse_workstamps(filename):
    """
    Parsing the file returns a list of lists. Each sublist contains
    WorkItems inside a restarttotal block/report
    """
    state = initial_state
    context = ParserContext()
    for item in itemify(filename):
        state = state(context, item)
    context.add_current_report()
    return context.reports


##############################################################################
# Filtering and transforming the data from the parser: specific customer,
# specific report and adding statistics
##############################################################################
def filter_report(report, items):
    """
    Filter workitems based on which report we need.

    None for everything. A number for a specific report starting from 0 the
    latest, 1 the previous, ....
    """
    if report is None:
        return items
    return (items[-1 * report],)


def filter_customer(customer, items):
    """Filter workitems based on a specific customer"""
    if customer is None:
        return items
    new_items = []
    for group in items:
        newgroup = [wp for wp in group if wp.customer == customer]
        if not newgroup:
            continue
        new_items.append(newgroup)
    return new_items


def stats_by_day(items):
    """Transforms the workitems groups into a list of reports that contains
    days and those days contains work items"""
    new_items = []
    for group in items:
        day = []
        previous = group[0].date
        new_group = []
        for item in group:
            if previous != item.date and day:
                new_group.append(WorkDay(day))
                previous = item.date
                day = []
            day.append(item)
        if day:
            new_group.append(WorkDay(day))
        new_items.append(WorkReport(new_group))
    return new_items


class WorkDay(list):
    """Wraps a group of days with statistics"""
    def __init__(self, items):
        super(WorkDay, self).__init__(items)
        self.customers = self.__totals()

    def __totals(self):
        """Builds customer totals for a day items"""
        totals = {}
        for item in self:
            if item.customer not in totals:
                totals[item.customer] = item.duration
                continue
            totals[item.customer] += item.duration
        return totals

    @property
    def date(self):
        """Date fo the work day"""
        return self[0].date


class WorkReport(list):
    """Group of days (restarttotals) providing customer statistics"""
    def __init__(self, days):
        super(WorkReport, self).__init__(days)
        self.customers = self.__totals()

    def __totals(self):
        """Builds customer totals for many days in a report"""
        totals = {}
        for day in self:
            for customer, total in day.customers.items():
                if customer not in totals:
                    totals[customer] = total
                    continue
                totals[customer] += total
        return totals


##############################################################################
# Output in text. Build report lines and format timedeltas
##############################################################################
def format_timestamp(delta):
    """Formats a timedelta in Hours:minutes string"""
    hours, remaining_seconds = divmod(delta.seconds, 3600)
    minutes = remaining_seconds / 60
    # We always measure entire minutes
    assert remaining_seconds % 60 == 0
    hours = hours + delta.days * 24
    return '%d:%02d' % (hours, minutes)


class TextReport(object):
    """Text report from stats per day data"""
    def __init__(self, report_data):
        self.report_data = report_data
        self.__lines = None

    @property
    def lines(self):
        """Get the report lines as a list of strings"""
        if self.__lines is not None:
            return self.__lines

        self.__lines = []
        for report in self.report_data:
            for day in report:
                self.__build_day(day)
            self.__summary(report)

        return self.__lines

    @property
    def text(self):
        """Get the report as one string"""
        return '\n'.join(self.lines)

    def __build_day(self, day):
        """Adds lines for a day report"""
        self.__lines.append("---------- %s ----------" % day.date)

        def item_format(work):
            """format a work item into a string"""
            duration = format_timestamp(work.duration)
            return '%s %s %s' % (duration, work.customer, work.description)
        self.__lines.extend([item_format(wp) for wp in day])
        self.__customer(day.customers)

    def __summary(self, report):
        """adds summary lines for customer totals in a day"""
        self.__lines.append('---------------------------------------------')
        self.__customer(report.customers, 'restart totals: ')
        self.__lines.append('')

    def __customer(self, customers, prefix=''):
        """Add lines for totals"""
        def fmt(customer, totals):
            """Formats a customer and its time totals"""
            totals = format_timestamp(totals)
            return '%s%s: %s' % (prefix, customer, totals)
        self.__lines.extend([fmt(c, t) for c, t in customers.items()])


##############################################################################
# Command line execution and argument parsing
##############################################################################
def cmdline_arguments():
    """Parse the command line arguments via argparse"""
    parser = ArgumentParser(description='.workstampts.txt report tool')
    parser.add_argument(
        'week', type=int, default=None, nargs='?',
        help='Report a specific week (default: all weeks)')
    parser.add_argument(
        '--customer', '-c',
        help='report for a customer (default: all customers)')
    parser.add_argument(
        '--file', '-f', default=expanduser('~/.workstamps.txt'),
        help='Input filename (default: ~/.workstamps.txt)')
    return parser.parse_args()


def run_from_command_line():
    """Run the report with command line arguments"""
    args = cmdline_arguments()
    print(TextReport(
        stats_by_day(
            filter_customer(
                args.customer, filter_report(
                    args.week, parse_workstamps(
                        args.file))))).text)


if __name__ == '__main__':
    run_from_command_line()
