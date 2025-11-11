.. _macos_compatibility:

macOS Compatibility Guide
==========================

The Irchel Geoparser requires Python with SQLite extension loading support. Unfortunately, the default macOS system Python and Python installed from the official Python website do not support loading SQLite extensions, which are essential for the library's gazetteer functionality (SpatiaLite for spatial indexing and Spellfix for fuzzy matching).

This guide walks you through setting up Python via Homebrew, which includes SQLite compiled with extension loading support. After completing these steps, you can return to the :doc:`installation` page and follow the standard installation instructions.

Step 1: Install Homebrew
-------------------------

If you don't already have Homebrew installed, install it by running:

.. code-block:: bash

   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

After installation completes, you need to add Homebrew to your PATH.

For **Apple Silicon Macs (M1/M2/M3)**:

.. code-block:: bash

   echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc

.. code-block:: bash

   source ~/.zshrc

For **Intel Macs**:

.. code-block:: bash

   echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc

.. code-block:: bash

   source ~/.zshrc

Step 2: Install Python via Homebrew
------------------------------------

Install Python using Homebrew:

.. code-block:: bash

   brew install python@3.13

This installs Python 3.13 with SQLite extension support enabled.

Step 3: Set Up Python and pip Symbolic Links
---------------------------------------------

To ensure you can use ``python`` and ``pip`` commands directly (rather than ``python3.13`` and ``pip3.13``), create symbolic links:

For **Apple Silicon Macs (M1/M2/M3)**:

.. code-block:: bash

   ln -s /opt/homebrew/bin/python3.13 /opt/homebrew/bin/python

.. code-block:: bash

   ln -s /opt/homebrew/bin/pip3.13 /opt/homebrew/bin/pip

For **Intel Macs**:

.. code-block:: bash

   ln -s /usr/local/bin/python3.13 /usr/local/bin/python

.. code-block:: bash

   ln -s /usr/local/bin/pip3.13 /usr/local/bin/pip

Step 4: Verify SQLite Extension Support
----------------------------------------

Verify that your Python installation supports SQLite extensions:

.. code-block:: bash

   python -c "import sqlite3; conn = sqlite3.connect(':memory:'); print('SQLite extension support:', hasattr(conn, 'enable_load_extension')); conn.close()"

You should see:

.. code-block:: text

   SQLite extension support: True

If you see ``False``, the Python installation does not support extensions and the geoparser will not work correctly.

Next Steps
----------

Your macOS system is now ready to use the Irchel Geoparser! Return to the :doc:`installation` page to install the library and download a gazetteer.
