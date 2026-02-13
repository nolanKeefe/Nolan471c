Within syntax.py l1

We are now missing Nat as an option for indexing, in specific this will affect our memory allocation and accessing classes.

Programs tag is now l1 and it's body is a Statement rather than a Term. Explained more in its effect below 

Statement is similar to Term in its actual application however it has a differing Annotated list than L2. It gets rid of things that make variables less direct making the variables more explicit

It now has copy and halt while at the same time getting rid of let, reference, and begin

Copy works to take the value of one variable and store it in another 
the destination is where you store the copy while the source is where you are copying from

Then is a statement used in a few classes and it simply works to say what the next line in the program is/the next statement to execute

Abstract still makes functions but now is storing it in a named variable unlike the others where it wasn't stored in such a manner.

Apply is just generally more explicit now having the argument be a sequence of strings rather than Terms. It still works to call the functions made by abstract. Interestingly it lacks the Then that most other classes have as the arguments themselves are moving you to the next action. It should take the function variable and then the variables being passed into the function.

Immediate loads an integer into a variable. The destination being the variable and the value being the integer that gets stored.

Primitive stores a value into a variable but instead uses operators on 2 given identifiers to obtain the thing being stored. Basically its doing the math as per the previous just with the additional specification of destination/where.

Branch is still an if else statement with the options of < and == applied on the left and right having a then statement if it passes and an otherwise if it fails. the then statement enters the if and the otherwise enters the else.

Allocate creates a space in memory of a size greater than or equal to 0 and then stores the location (a pointer)

Load reads the location in memory to a variable. destination being the variable we store to, base being the pointer to memory (I think?) and index being the cell in memory to read

Store saves a value to a location in memory using the pointer. It stores to index using value

Halt is the end of the program and returns a value