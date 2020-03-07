# dit - The universal container file

Interface for working with .dit files

![Short Demo](docs/gifs/short.gif)

Dit is a new way of storing data, designed to be as generic as possible. It uses embedded scripts for validation, custom print functions, and more. Dits can be used to transport data across different formats and platforms, so sharing data is much easier. See more at [the official website.](https://www.ditabase.io/)

## Install

    pip install dit-cli

Dit can be installed with [pip for python](https://pip.pypa.io/en/stable/installing/). Note that you will need Python 3.8.

## Usage

    dit validate [filename]
Validate a dit file. Returns either an error message, or 'dit is valid, no errors found'

    dit query [filename] [query_string]
Validate a dit file, and then return a value based on the query. A query should resemble a `@@` variable sequence found in dit code.

    '@@top_level_object' -> serialize the entire object
    '@@top_level_object.some_value' -> serialize that value, whatever it is
    '@@print(top_level_object) -> Use the object's print function, if it has one.

## dit quickstart

To start, you'll need a dit. You can see examples in [tests/dits](tests/dits).

Let's make a simple dit, `name.dit`:

```
Name {
    String value;
}
```

This is a dit class, with a single contained (instance) variable. String is the only primitive type. Everything in dit is either a string, object, or a list.

Now that we have a class, we can make an object and assign it.

```
Name name;
name.value = 'John';
```

Great! Now we can get the stored name by querying the file:

    dit query name.dit @@name.value
    "John"

The double at symbol `@@` is the dit escape sequence, used to reference variables in code and query strings. Variables are always referenced as `.` operations. You can also just ask for the entire `name` object, rather than a specific part:

    dit query name.dit @@name
    {"class":"Name","value":"John"}

The default print language is Javascript, but this is highly configurable. Let's add a custom print function.

```
Name {
    String value;
    print Python {{
        return 'My name is ' + @@value
    }}
}
```

Dit will interpret everything in the double brace `{{}}` section as Python code, and use it to build a Python file. `@@value` will be converted into a Python compatible string before running the code. You can see all the language configurations in ~/.dit-languages. This is how new languages will be added and customized.

    dit query name.dit '@@print(name)'
    "My name is John"

`print` will activate a print function, if one is present. It will always return something relevant. If you want, you can also `print value;` which will make the object resolve to that variable, rather than serializing the whole thing.

But we have a problem: There's nothing to stop something like this:

    dit query name.dit '@@print(name)'
    "My name is 4jZw3ef\n"

We need to make sure it's really a name. Let's add a validator!

```
Name {
    String value;
    print Python {{
        return 'My name is ' + @@value
    }}
    validator Javascript {{
        // Let's use Javascript here, I like the regex syntax better.
        let name = @@value;
        if (!/^[A-Z][A-z]+$/.test(name)) {
            return `Not a valid name: "${name}"`
        }
        return true;
    }}
}
```

If a validator returns any value other than 'true' (case insensitive), that value is assumed to be an error message, and will cause a `ValidationError`.

    dit query name.dit '@@print(name)'
    ValidationError<name>: Not a valid name: "4jZw3ef\n"

Now let's make this a little more interesting. How about a `FullName` class?

```
FullName {
    Name givenName;
    list Name middleNames;
    Name familyName;
    print Python {{
        full = @@givenName
        for mid in @@middleNames:
            full += ' ' + mid
        full += ' ' + @@familyName
        return full
    }}
}
```

A full name contains several Name objects. `middleNames` is a list, since people can have multiple middle names. The print function nicely puts everything together.

Now we still have the `name` variable from before, but we don't want to have to manually create a different variable for each object.

```
Name firstName;
Name middleName1;
Name middleName2;//This would be awful
```

So, we can use an Assigner, which will create an anonymous object for us on the fly. Assigners can only have assignment statements currently, but they will probably look more like arbitrary functions in the future.

```
Name n(name) {
    value = name;
}

FullName myName;

// Assign an existing object
myName.givenName = name;

// Use the 'n' assigner inside a list
myName.middleNames = [n('Leopold'), n('Koser')];

// Assign the string directly
myName.familyName.value = 'Shiner';
```

Cool! Let's give it a try:

    dit query name.dit '@@print(myName)'
    "Hi! My name is Isaiah Leopold Koser Shiner"
