Changelog
============


2.4 (2012-10-14)
----------------
- Add a log limit property to logs to limit memory & other resources usage [kiorky]
- Performance tweaks [kiorky]


2.3 (2012-10-11)
----------------
- better registry handling [kiorky]
- better jobrunner [kiorky]
- better tests  [kiorky]
- make install and restart code more robust, again [kiorky]

2.2 (2012-10-11)
----------------

- make install and restart code more robust.
  This is **release codename Wine**. A really thanks to Andreas Jung which helped me to find a difficult bug
  with ZODB transactions. (call transaction.savepoint to make _p_jar which was None to appear).
  [kiorky]


2.1 (2012-10-10)
----------------

- better tests for addons consumers [kiorky]


2.0 (2012-10-10)
----------------
- Rewrite collective.cron for better robustness, documentation & no extra dependencies on content types
  [kiorky]



1.0 (2011)
----------------
- First release

