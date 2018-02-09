yt_archive
==========

Web application for tracking progress while watching YouTube channel videos,
archiving them using youtube-dl and downloading their comments.

Installation
------------

.. code-block:: bash

   python setup.py install

Client secret
-------------

**!!! IMPORTANT !!!**

Application uses Youtube Data API with OAuth 2.0, therefore client secret file
is needed. See guide_ how to obtain it. Place it in application's root directory.

.. _guide: https://developers.google.com/youtube/v3/quickstart/python#step_1_turn_on_the_api_name

Usage
-----

.. code-block:: bash

   python -m yt_archive run

or

.. code-block:: bash

   yt_archive run

Testing
-------

.. code-block:: bash

   pip install -r requirements.txt

.. code-block:: bash

   python setup.py test

Documentation
-------------

.. code-block:: bash

   pip install -r requirements.txt

.. code-block:: bash

   cd docs && make html && cd ..
   xdg-open docs/_build/html/index.html

License
-------

This project is licensed under the MIT License - see the
`LICENSE <../../../LICENSE>`_ file for more details.
