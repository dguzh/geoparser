"""
Implementations of the three build pipeline stages (see :mod:`..builder`).

Each module here performs one stage's actual work and reports its own
progress items: :mod:`acquire` and :mod:`staging` together make up
"Preparing sources", :mod:`compile` makes up "Compiling features" (though
its compiled SQL is run, and its progress reported, by the builder itself),
and :mod:`emit` makes up "Building artifact".
"""
