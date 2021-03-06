import inspect
import sys


def get_callee_frame_info():
    callee_frame = inspect.stack()[2]
    if sys.version_info < (3, 5):
        debug_info = callee_frame[1], callee_frame[2]
    else:
        debug_info = callee_frame.filename, callee_frame.lineno
    return debug_info


def debug_wire(fn):
    """
    Automatically populates the `debug_info` argument for a wire call if it's
    not already passed as an argument
    """
    # TODO: We could check that fn has the correct interface 
    #       wire(i, o, debug_info)
    def wire(i, o, debug_info=None):
        if debug_info is None:
            debug_info = get_callee_frame_info()
        return fn(i, o, debug_info)
    return wire

