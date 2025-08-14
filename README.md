# fylang

`pip install fylang`


## Description
Welcome to fylang!

fylang is my own language created on Python. The motivation for this language came from wanting to be able to write extremely cursed one liners easily. Therefore, most things can be used as expressions and evaluate to a value.

### Variables
Simple assignment based variables. Make sure to add a semi-colon after every line.
```
// the language is dynamically typed so
// anything can be assigned to a variable
variable_name = 1;
```

### Control Flow
if-else's evaluate to the value of whatever branch becomes true. In case you just want a single expression inside the if-else's without the `{}`, you can simply omit them as well.
```
math = import('math');

x = 2;
y = none;
if x == 1 {
  y = math.pow(x, 4);
} else {
  y = math.pow(4, x);
};

print(y);
```
### Functions
Functions can be created with or without `{}`.
```
unnamed_function = fn(a, b) -> {
  return a + b;
};

fn named_function(a, b) -> a + b;

// you can also use variable arguments
// variable arguments must be the last
// parameter in function declaration

fn function_with_varargs(...args) -> {
  // do something with the varargs
};
```
### Lists, Dictionaries, Tuples
All of the containers are directly taken from python. That also means all the methods associated with these containers share the same names as in python.

```
myList = [1, 2, 3];
myList.append(4);
print(myList); // [1, 2, 3, 4]

myDict = {
  "hello": "world",
  "goodbye": "world"
};

myTuple = (1,);
```
###### Disclaimer: sets have not beed added yet

### Structs
Despite being called structs, they act more like javascript objects than anything. They can also be both named and unnamed.
```
// unassigned properties default to 'none'
struct Node {
  val,
  next = none
};

// you can use either keyword args
// or pass them in normally
head = Node(val=1, none);
head.next = Node(2);


struct Adder {
  a = 0,
  b = 0,
  run = fn() -> this.a + this.b
};

addr = Adder();
addr.a = 2;
addr.b = 3;
print(addr.run()); // 5
```
