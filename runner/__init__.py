"""Runner — the experiment orchestration layer.

This package is a thin middle layer between the user and the execution code
(generate/, explain/, utils/). It owns *how* an experiment is described and
run (naming, validation, ordering, progress); the actual generation/checking
logic stays in the execution modules and is delegated to unchanged.
"""
