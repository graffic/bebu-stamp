Bebu Time tracker
======================

Simple shell time tracker. Based on `betabug`_ `stamp`_ time tracker.

The functionality might be dummy, but this clone was created as an exercise
about:

- Code simplicity
- Testability
- Features
- Implications of the above in performance

.. code-block::

    141480 function calls (141366 primitive calls) in 1.068 seconds
    vs
    46054 function calls (46016 primitive calls) in 0.284 seconds

Usage
-----

Download this repo and use the stamp and days_calc.py commands.

To start working just write stamp. This will mark in the tracker that you're
working.

.. code-block:: bash

   $ stamp

After you've finished your work tell the tracker for who and what you did.

.. code-block:: bash

   $ stamp myclient I did this and that


To get reports use the ``days_calc`` tool.

.. code-block:: bash

   $ days_calc.py
   ---------- 2013-11-08 ----------
   00:12 myclient I did this and that
   myclient: 00:12
   ---------------------------------------------
   restart totals: myclient: 00:12

Advanced usage
--------------

Data is written to a text file. By default it uses ``~/.workstamps.txt``. You
can divide the work stamps file into reports by inserting the ``restarttotals``
keyword.

.. code-block:: bash

    2013-11-08 11:00 start
    2013-11-08 11:12 myclient I did this and that
    ...
    2013-11-12 09:12 myclient I did this and that
    restarttotals
    2013-11-13 09:12 start
    ...

Put these restart totals after a day finished in order to get meaningful
reports.

After that you can use the ``days_calc.py`` tool to get specific reports

.. code-block:: bash

   $ days_calc.py 1  # Print only the previous report to the current

License
-------

Uses the `MIT`_ license.

.. _betabug: http://betabug.ch/
.. _stamp: http://repos.betabug.ch/stamp/
.. _MIT: http://opensource.org/licenses/MIT
