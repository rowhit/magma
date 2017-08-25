from magma.t import Type
from magma.bit import Bit, BitType, In, Out
from magma.clock import Clock, ClockEnable, Reset
from magma.bits import Bits, BitsType, SInt, SIntType, UInt, UIntType
from magma.circuit import DeclareCircuit, circuit_type_method
from magma.compatibility import IntegerTypes
from magma.bit_vector import BitVector
from magma.wire import wire
from magma.conversions import array, bits, uint, sint
import operator
import math
try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

__all__  = ['and_', 'or_', 'xor'] 
__all__ += ['invert']
__all__ += ['eq', 'ne']
__all__ += ['lshift', 'rshift']
__all__ += ['add', 'sub', "mul", "div", "truediv"]
__all__ += ['lt', 'le', "gt", "ge"]
__all__ += ['concat', 'replicate']
__all__ += ['zext', 'sext']

def type_check_binary_operator(operator):
    """
    For binary operations, the other argument must be the same type or a list
    of bits of the same length
    """
    def type_checked_operator(self, other):
        if not (isinstance(other, list) and len(self) == len(other)) and \
           type(self) != type(other):
            raise TypeError("unsupported operand type(s) for {}: '{}' and"
                            "'{}'".format(operator.__name__, type(self),
                                          type(other)))
        return operator(self, other)
    return type_checked_operator


def declare_bit_binop(name, op, python_op, firrtl_op):
    def simulate(self, value_store, state_store):
        in0 = BitVector(value_store.get_value(self.in0))
        in1 = BitVector(value_store.get_value(self.in1))
        out = python_op(in0, in1).as_bool_list()[0]
        value_store.set_value(self.out, out)
    circ = DeclareCircuit("{}_bit".format(name),
                          'in0', In(Bit), 'in1', In(Bit), 'out', Out(Bit),
                          simulate=simulate,
                          firrtl_op=firrtl_op,
                          verilog_name=name)

    @type_check_binary_operator
    def func(self, other):
        return circ(width=1)(self, other)
    func.__name__ = op
    setattr(BitType, op, func)


declare_bit_binop("coreir_and", "__and__", operator.and_, "and")
declare_bit_binop("coreir_or", "__or__", operator.or_, "or")
declare_bit_binop("coreir_xor", "__xor__", operator.xor, "xor")

def simulate_bit_not(self, value_store, state_store):
    _in = BitVector(value_store.get_value(getattr(self, "in")))
    out = (~_in).as_bool_list()[0]
    value_store.set_value(self.out, out)

BitInvert = DeclareCircuit("coreir_not0", 'in', In(Bit), 'out', Out(Bit),
        simulate=simulate_bit_not, verilog_name="coreir_not")


def __invert__(self):
    return BitInvert(width=1)(self)


BitType.__invert__ = __invert__


def declare_bits_binop(name, op, python_op):
    def simulate(self, value_store, state_store):
        in0 = BitVector(value_store.get_value(self.in0))
        in1 = BitVector(value_store.get_value(self.in1))
        out = python_op(in0, in1).as_bool_list()
        value_store.set_value(self.out, out)

    @lru_cache(maxsize=None)
    def Declare(N):
        T = Bits(N)
        return DeclareCircuit("{}{}".format(name, N),
                              'in0', In(T), 'in1', In(T), 'out', Out(T),
                              simulate=simulate,
                              verilog_name=name)

    @type_check_binary_operator
    def func(self, other):
        return Declare(self.N)(width=self.N)(self, other)
    func.__name__ = op
    setattr(BitsType, op, func)


declare_bits_binop("coreir_and", "__and__", operator.and_)
declare_bits_binop("coreir_or", "__or__", operator.or_)
declare_bits_binop("coreir_xor", "__xor__", operator.xor)


def simulate_bits_not(self, value_store, state_store):
    _in = BitVector(value_store.get_value(getattr(self, "in")))
    out = (~_in).as_bool_list()
    value_store.set_value(self.out, out)

@lru_cache(maxsize=None)
def DeclareInvertN(N):
    T = Bits(N)
    return DeclareCircuit("coreir_not{}".format(N), 'in', In(T), 'out', Out(T),
            simulate=simulate_bits_not, verilog_name="coreir_not")


def __invert__(self):
    return DeclareInvertN(self.N)(width=self.N)(self)


BitsType.__invert__ = __invert__


def __lshift__(self, other):
    N = self.N
    T = Bits(N)
    if isinstance(other, IntegerTypes):
        if other < 0:
            raise ValueError("Second argument to << must be positive, not "
                    "{}".format(other))

        def simulate_shift_left(self, value_store, state_store):
            _in = BitVector(value_store.get_value(getattr(self, "in")))
            out = _in << other
            value_store.set_value(self.out, out.as_bool_list())

        circ = DeclareCircuit("coreir_shl{}".format(N), 'in', In(UInt(N)),
                'out', Out(T), verilog_name="coreir_shl",
                simulate=simulate_shift_left)
        return circ(width=N, SHIFTBITS=other)(self)
    elif isinstance(other, Type):
        if not isinstance(other, UIntType):
            raise TypeError("Second argument to << must be a UInt, not "
                    "{}".format(type(other)))
        def simulate(self, value_store, state_store):
            in0 = BitVector(value_store.get_value(self.in0))
            in1 = BitVector(value_store.get_value(self.in1))
            out = (in0 << in1).as_bool_list()
            value_store.set_value(self.out, out)

        circ = DeclareCircuit("coreir_dshl{}".format(N), 'in0', In(T), 'in1',
                In(UInt(N)), 'out', Out(T), verilog_name="coreir_dshl",
                simulate=simulate)
        return circ(width=N)(self, other)
    else:
        raise TypeError("<< not implemented for argument 2 of type {}".format(
            type(other)))


BitsType.__lshift__ = __lshift__

def __rshift__(self, other):
    N = self.N
    T = Bits(N)
    if isinstance(other, IntegerTypes):
        if other < 0:
            raise ValueError("Second argument to >> must be positive, not "
                    "{}".format(other))

        def simulate_shift_left(self, value_store, state_store):
            _in = BitVector(value_store.get_value(getattr(self, "in")))
            out = _in >> other
            value_store.set_value(self.out, out.as_bool_list())

        circ = DeclareCircuit("coreir_lshr{}".format(N), 'in', In(UInt(N)),
                'out', Out(T), verilog_name="coreir_lshr",
                simulate=simulate_shift_left)
        return circ(width=N, SHIFTBITS=other)(self)
    elif isinstance(other, Type):
        if not isinstance(other, UIntType):
            raise TypeError("Second argument to >> must be a UInt, not "
                    "{}".format(type(other)))
        def simulate(self, value_store, state_store):
            in0 = BitVector(value_store.get_value(self.in0))
            in1 = BitVector(value_store.get_value(self.in1))
            out = (in0 >> in1).as_bool_list()
            value_store.set_value(self.out, out)

        circ = DeclareCircuit("coreir_dlshr{}".format(N), 'in0', In(T), 'in1',
                In(UInt(N)), 'out', Out(T), verilog_name="coreir_dlshr",
                simulate=simulate)
        return circ(width=N)(self, other)
    else:
        raise TypeError(">> not implemented for argument 2 of type {}".format(
            type(other)))


BitsType.__rshift__ = __rshift__


def declare_binop(name, _type, type_type, op, python_op, out_type=None):
    signed = type_type is SIntType
    def simulate(self, value_store, state_store):
        in0 = BitVector(value_store.get_value(self.in0), signed=signed)
        in1 = BitVector(value_store.get_value(self.in1), signed=signed)
        out = python_op(in0, in1).as_bool_list()
        if out_type is Bit:
            assert len(out) == 1, "out_type is Bit but the operation returned a list of length {}".format(len(out))
            out = out[0]
        value_store.set_value(self.out, out)

    @lru_cache(maxsize=None)
    def Declare(N):
        T = _type(N)
        return DeclareCircuit("{}{}".format(name, N),
                              'in0', In(T), 'in1', In(T),
                              'out', Out(out_type if out_type else T),
                              stateful=False,
                              simulate=simulate,
                              verilog_name=name)

    @type_check_binary_operator
    def func(self, other):
        return Declare(self.N)(width=self.N)(self, other)
    func.__name__ = op
    setattr(type_type, op, func)

declare_binop("coreir_eq", Bits, BitsType, "__eq__", operator.eq, out_type=Bit)

declare_binop("coreir_add", SInt, SIntType, "__add__", operator.add)
declare_binop("coreir_sub", SInt, SIntType, "__sub__", operator.sub)
declare_binop("coreir_mul", SInt, SIntType, "__mul__", operator.mul)
declare_binop("coreir_sdiv", SInt, SIntType, "__div__", operator.truediv)
declare_binop("coreir_sdiv", SInt, SIntType, "__truediv__", operator.truediv)
declare_binop("coreir_slt",  SInt, SIntType, "__lt__", operator.lt, out_type=Bit)
declare_binop("coreir_sle", SInt, SIntType, "__le__", operator.le, out_type=Bit)
declare_binop("coreir_sgt",  SInt, SIntType, "__gt__", operator.gt, out_type=Bit)
declare_binop("coreir_sge", SInt, SIntType, "__ge__", operator.ge, out_type=Bit)

declare_binop("coreir_add", UInt, UIntType, "__add__", operator.add)
declare_binop("coreir_sub", UInt, UIntType, "__sub__", operator.sub)
declare_binop("coreir_mul", UInt, UIntType, "__mul__", operator.mul)
declare_binop("coreir_udiv", UInt, UIntType, "__div__", operator.truediv)
declare_binop("coreir_udiv", UInt, UIntType, "__truediv__", operator.truediv)
declare_binop("coreir_ult",  UInt, UIntType, "__lt__", operator.lt, out_type=Bit)
declare_binop("coreir_ule", UInt, UIntType, "__le__", operator.le, out_type=Bit)
declare_binop("coreir_ugt",  UInt, UIntType, "__gt__", operator.gt, out_type=Bit)
declare_binop("coreir_uge", UInt, UIntType, "__ge__", operator.ge, out_type=Bit)


def arithmetic_shift_right(self, other):
    N = self.N
    T = SInt(N)
    if isinstance(other, IntegerTypes):
        if other < 0:
            raise ValueError("Second argument to arithmetic_shift_right must be "
                    "positive, not {}".format(other))

        def simulate_arithmetic_shift_right(self, value_store, state_store):
            _in = BitVector(value_store.get_value(getattr(self, "in")), signed=True)
            out = _in.arithmetic_shift_right(other)
            value_store.set_value(self.out, out.as_bool_list())
        circ =  DeclareCircuit("coreir_ashr{}".format(N), 'in', In(UInt(N)),
                'out', Out(T), verilog_name="coreir_ashr",
                simulate=simulate_arithmetic_shift_right)
        return circ(width=self.N, SHIFTBITS=other)(self)
    elif isinstance(other, Type):
        if not isinstance(other, UIntType):
            raise TypeError("Second argument to arithmetic_shift_right must be "
                    "a UInt, not {}".format(type(other)))

        def simulate(self, value_store, state_store):
            in0 = BitVector(value_store.get_value(self.in0), signed=True)
            in1 = BitVector(value_store.get_value(self.in1))
            out = in0.arithmetic_shift_right(in1).as_bool_list()
            value_store.set_value(self.out, out)

        circ = DeclareCircuit("coreir_dashr{}".format(N), 'in0', In(T), 'in1',
                In(UInt(N)), 'out', Out(T), verilog_name="coreir_dashr",
                simulate=simulate)
        return circ(width=self.N)(self, other)
    else:
        raise TypeError(">> not implemented for argument 2 of type {}".format(
            type(other)))


SIntType.arithmetic_shift_right = arithmetic_shift_right


def gen_sim_register(N, has_ce, has_reset):
    def sim_register(self, value_store, state_store):
        """
        Adapted from Brennan's SB_DFF simulation in mantle
        """
        cur_clock = value_store.get_value(self.clk)

        if not state_store:
            state_store['prev_clock'] = cur_clock
            state_store['cur_val'] = BitVector(0, num_bits=N)

        if has_reset:
            cur_reset = value_store.get_value(self.rst)
        # if s:
        #     cur_s = value_store.get_value(self.S)

        prev_clock = state_store['prev_clock']
        # if not n:
        #     clock_edge = cur_clock and not prev_clock
        # else:
        #     clock_edge = not cur_clock and prev_clock
        clock_edge = cur_clock and not prev_clock

        new_val = state_store['cur_val'].as_bool_list()

        if clock_edge:
            input_val = value_store.get_value(getattr(self, "in"))

            enable = True
            if has_ce:
                enable = value_store.get_value(self.en)

            if enable:
                # if r and sy and cur_r:
                #     new_val = False
                # elif s and sy and cur_s:
                #     new_val = True
                # else:
                #     new_val = input_val
                new_val = input_val

        if has_reset and not cur_reset:  # Reset is asserted low
            new_val = [False for _ in range(N)]
        # if s and not sy and cur_s:
        #     new_val = True

        state_store['prev_clock'] = cur_clock
        state_store['cur_val'] = BitVector(new_val, num_bits=N)
        value_store.set_value(self.out, new_val)
    return sim_register

@lru_cache(maxsize=None)
def DefineRegister(N, has_ce=False, has_reset=False, T=Bits):
    name = "coreir_reg_P"  # TODO: Add support for clock interface
    io = ["in", In(T(N)), "clk", In(Clock), "out", Out(T(N))]
    methods = []

    def reset(self, condition):
        wire(condition, self.rst)
        return self

    if has_reset:
        io.extend(["rst", In(Reset)])
        name += "R"  # TODO: This assumes ordering of clock parameters
        methods.append(circuit_type_method("reset", reset))

    def when(self, condition):
        wire(condition, self.en)
        return self

    if has_ce:
        io.extend(["en", In(ClockEnable)])
        name += "E"  # TODO: This assumes ordering of clock parameters
        methods.append(circuit_type_method("when", when))

    def wrapper(*args, **kwargs):
        return DeclareCircuit(
            name,
            *io,
            stateful=True,
            simulate=gen_sim_register(N, has_ce, has_reset),
            circuit_type_methods=methods
        )(width=N, *args, **kwargs)
    return wrapper


def DefineMux(N):
    def simulate(self, value_store, state_store):
        in0 = BitVector(value_store.get_value(self.in0))
        in1 = BitVector(value_store.get_value(self.in1))
        sel = BitVector(value_store.get_value(self.sel))
        out = in1 if sel.as_int() else in0
        value_store.set_value(self.out, out)
    def wrapper(*args, **kwargs):
        return DeclareCircuit("coreir_mux".format(N), 
            *["in0", In(Bits(N)), "in1", In(Bits(N)), "sel", In(Bit), 
             "out", Out(Bits(N))],
            verilog_name="coreir_mux",
            simulate=simulate
        )(width=N, *args, **kwargs)
    return wrapper


def and_(self, rhs):
    return self & rhs

def or_(self, rhs):
    return self | rhs

def xor(self, rhs):
    return self ^ rhs

def invert(self):
    return ~self

def add(self, rhs):
    return self + rhs

def sub(self, rhs):
    return self - rhs

def mul(self, rhs):
    return self * rhs

def div(self, rhs):
    return self / rhs

def truediv(self, rhs):
    return self // rhs

def eq(self, rhs):
    return self == rhs

def ne(self, rhs):
    return self != rhs

def lt(self, rhs):
    return self < rhs

def le(self, rhs):
    return self <= rhs

def gt(self, rhs):
    return self > rhs

def ge(self, rhs):
    return self >= rhs

def lshift(self, rhs):
    return self << rhs

def rshift(self, rhs):
    return self >> rhs

def replicate(value, n):
    return 

def concat(*arrays):
    ts = [t for a in arrays for t in a.ts] # flatten
    return array(ts)

def zext(value, n):
    assert isinstance(value, (UIntType, SIntType, BitsType))
    if isinstance(value, UIntType):
        zeros = uint(0,n)
    elif isinstance(value, SIntType):
        zeros = sint(0,n)
    elif isinstance(value, BitsType):
        zeros = bits(0,n)
    return concat(zeros,value)

def sext(value, n):
    assert isinstance(value, SIntType)
    return sint(concat(array(value[-1], n), array(value)))

#def mux(I0, I1, S):
#    assert isinstance(S, BitType)
#    assert isinstance(I0, BitType) or isinstance(I0, BitsType)
#    assert isinstance(I1, BitType) or isinstance(I1, BitsType)
#    assert type(I0) == type(I1)
#    if isinstance(I0, BitType):
#        return Mux(2)(I0, I1, S)
#    elif:
#        return Mux(2,len(I0))(I0, I1, S)


def DefineMem(width, depth):
    name = "coreir_mem{}{}".format(width, depth)
    is_power_of_two = lambda num: num != 0 and ((num & (num - 1)) == 0)
    assert is_power_of_two(width) and is_power_of_two(depth)
    IO = ["raddr", In(Bits(int(math.log2(depth)))), 
          "waddr", In(Bits(int(math.log2(depth)))), 
          "wdata", In(Bits(width)), 
          "rclk", In(Bit), 
          "ren", In(Bit), 
          "wclk", In(Bit), 
          "wen", In(Bit), 
          "rdata", Out(Bits(width))]
    circ = DeclareCircuit(name, *IO, verilog_name="coreir_mem", )
    def wrapper(*args, **kwargs):
        return circ(*args, width=width, depth=depth, **kwargs)
    return wrapper
