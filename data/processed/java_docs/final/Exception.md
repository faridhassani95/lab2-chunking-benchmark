# Class Exception
public class Exception
extends Throwable
The class `Exception` and its subclasses are a form of
`Throwable` that indicates conditions that a reasonable
application might want to catch.
The class `Exception` and any subclasses that are not also
subclasses of `RuntimeException` are *checked
exceptions*. Checked exceptions need to be declared in a
method or constructor's `throws` clause if they can be thrown
by the execution of the method or constructor and propagate outside
the method or constructor boundary.
Constructors
Modifier
Constructor
Description
`Exception()`
Constructs a new exception with `null` as its detail message.
`Exception(String message)`
Constructs a new exception with the specified detail message.
`Exception(String message,
Throwable cause)`
Constructs a new exception with the specified detail message and
cause.
`protected`
`Exception(String message,
Throwable cause,
boolean enableSuppression,
boolean writableStackTrace)`
Constructs a new exception with the specified detail message,
cause, suppression enabled or disabled, and writable stack
trace enabled or disabled.
`Exception(Throwable cause)`
Constructs a new exception with the specified cause and a detail
message of `(cause==null ? null : cause.toString())` (which
typically contains the class and detail message of `cause`).
### Methods declared in class java.lang.Throwable
`addSuppressed, fillInStackTrace, getCause, getLocalizedMessage, getMessage, getStackTrace, getSuppressed, initCause, printStackTrace, printStackTrace, printStackTrace, setStackTrace, toString`
### Methods declared in class java.lang.Object
`clone, equals, finalize, getClass, hashCode, notify, notifyAll, wait, wait, wait`
+ ### Exception
public Exception()
Constructs a new exception with `null` as its detail message.
The cause is not initialized, and may subsequently be initialized by a
call to `Throwable.initCause(java.lang.Throwable)`).
+ ### Exception
public Exception(String message)
Constructs a new exception with the specified detail message. The
cause is not initialized, and may subsequently be initialized by
a call to `Throwable.initCause(java.lang.Throwable)`).
Parameters:
:   `message` - the detail message. The detail message is saved for
later retrieval by the `Throwable.getMessage()`) method.
+ ### Exception
public Exception(String message,
Throwable cause)
Constructs a new exception with the specified detail message and
cause.
Note that the detail message associated with
`cause` is *not* automatically incorporated in
this exception's detail message.
Parameters:
:   `message` - the detail message (which is saved for later retrieval
by the `Throwable.getMessage()`) method).
:   `cause` - the cause (which is saved for later retrieval by the
`Throwable.getCause()`) method). (A `null` value is
permitted, and indicates that the cause is nonexistent or
unknown.)
+ ### Exception
public Exception(Throwable cause)
Constructs a new exception with the specified cause and a detail
message of `(cause==null ? null : cause.toString())` (which
typically contains the class and detail message of `cause`).
This constructor is useful for exceptions that are little more than
wrappers for other throwables (for example, `PrivilegedActionException`).
Parameters:
:   `cause` - the cause (which is saved for later retrieval by the
`Throwable.getCause()`) method). (A `null` value is
permitted, and indicates that the cause is nonexistent or
unknown.)
+ ### Exception
protected Exception(String message,
Throwable cause,
boolean enableSuppression,
boolean writableStackTrace)
Constructs a new exception with the specified detail message,
cause, suppression enabled or disabled, and writable stack
trace enabled or disabled.
Parameters:
:   `message` - the detail message.
:   `cause` - the cause. (A `null` value is permitted,
and indicates that the cause is nonexistent or unknown.)
:   `enableSuppression` - whether or not suppression is enabled
or disabled
:   `writableStackTrace` - whether or not the stack trace should
be writable