## Summary

Overhaul "assigners" into functions. This requires a variety of features and changes to
make functions consistent and useful.

## Motivation

Dit should allow a developer to:

- Create objects from any format, e.g. JSON, Spreadsheets, custom text, database query,
  API, etc.
- Print objects out as any format, write to a database, file, or API etc.
- Inherit the above functionality from pre-made formats/scripts/classes.
- Execute any dit statement in a script, e.g. declaring a new object, assigning a value.
- Execute any statement in any script, e.g. validation in a constructor, printing in a
  validator.
- Use all scripting functionality in the CLI.
- Use dit as a scripting engine, e.g. convert formats/schemas without ever loading the
  data into a dit.

Currently, dit data can only be created using strings in dit syntax, which violates the
principle of being able to take data from any format. Dit data can be printed in several
ways, but only one custom script per class. There are workarounds, but this is
inconvenient.

## Proposed Changes

To meet these requirements, there will now only be two significant concepts in dit
syntax: classes and scripts. All other syntax can exist within a script of any language,
including object declaration and assignment, validation, and printing. There is no
longer any explicit syntax concept of validation as being separate from printing, or
anything else. The only statements you can't execute inside scripts is reserved class
concepts, like

Here's what the basics of how this might look:

```
// Typed parameters, no return type
Python void SayHello(someObj: SomeParent) {

}

Name {
    extends SomeParent;
    String value;

    // Use an explicit attribute.
    printer = value;
    //

}
```

## New classes

Classes will now define a series of "public API" functions, which can be used by the CLI
or other classes or scripts. They can define these functions in the class, inherit the
functionality from a parent class, or specify a named script.

The API is as follows:

- **Validator**  
  Run automatically by dit to

# Ideas After walk (braindump ideas)

- Model after Java ~~C/C++~~
- Functions and class member functions
- A script is what goes in a function.
- Converting is a given with functions
- Member functions with Explicit class purposes is a little silly.
  `void Python validator val1() {{ #This seems a little silly? }}`
- If a member function has no purpose (it's just a procedure), then what is that called?
  nothing? Procedure? `void`?
- How does inheriting a function into a member function work? How do you specify which
  parameter is `this`? What if you want the other parameters to always have a new
  default/explicit value, WAAAAIITT Solution. Inherited functions works by defining a
  new function _and then just calling the other one._ To prevent inefficiencies, you can
  use dit lang scripts, discussed next.
- dit lang, the equivalent of raw dit syntax, but usable to execute a repeated series of
  dit syntax statements, like assigning constants, calling functions, or generating
  stuff.
- There should be certain built in functions, like printing to the CLI, as in
  `print(anything)`. This means `print` for classes probably needs to become toString.
  `validate` is another one, tho this is tied in with classes, because you should be
  able to do `someObject.validate()` as well as `validate(someObject)`. I'm not sure how
  exactly this should work.
- Classes need constructors, but should it be `new` or something like that?
- should validation be activated automatically after parsing, or controlled by the dit
  itself/manually in the CLI? A script might want to validate an object before
  interacting with it, so it makes sense that it could tell that object to validate
  itself. but that means some objects are validated before the whole dit is parsed, so
  do I just validate the rest, or require an explicit `validateAll()` at the dnd of the
  dit?

Later features

- Expose everything to the CLI. For now, I can fudge the CLI changes.
- Throw/Try/Catch in dit syntax would be a cool feature. Have the catch go to a script.
- Natural serialization. Instead of getting `"The value"`, natural ser would give
  `The value`. If its a list, maybe `item1, item2, item3`. OH the solution for this is
  to have `English` as a lang! right? Probably not literally english, but something to
  that effect. Allow for configurable serialization languages that are intended for
  output rather than evaling into scripts.
- Overriding is a later feature. It would allow data to match a child object and be
  converted to match the parent, rather than matching parent and converted (using
  toString/Print) to match the child. If the child format is used in a constructor, the
  validation _must_ occur right there in the constructor, which is rather inconvenient.
