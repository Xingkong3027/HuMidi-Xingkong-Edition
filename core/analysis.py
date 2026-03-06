# Compatibility shim — each class/function has been moved to its own focused module.
# New code should import directly from the sub-modules below.
from core.humanizer import Humanizer                        # noqa: F401
from core.section_analyzer import SectionAnalyzer, assign_hands  # noqa: F401
import core.pedal_generator                                 # noqa: F401
