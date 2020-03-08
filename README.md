# dit - The universal container file
![Short Demo](https://raw.githubusercontent.com/isaiahshiner/dit-cli/master/docs/gifs/short.gif)

Dit is a new way of storing data, designed to be as generic as possible. It uses embedded scripts for validation, custom print functions, and more. Dits can be used to transport data across different formats and platforms, so sharing data is much easier. See more at [the official website.](https://www.ditabase.io/)

## Install

    pip install dit-cli

Dit can be installed with [pip for python](https://pip.pypa.io/en/stable/installing/). Note that you will need Python 3.8 and Node.js (for JS scripts).

## Usage

    dit validate [filename]
Validate a dit file. Returns either an error message, or 'dit is valid, no errors found'.

    dit query [filename] [query_string]
Validate a dit file, and then return a value based on a query string. A query should resemble a double at `@@` variable sequence found in dit code.

    '@@top_level_object' -> serialize the entire object
    '@@top_level_object.some_value' -> serialize that value, whatever it is
    '@@print(top_level_object)' -> Use the object's print function, if it has one.

## dit quickstart

To start, you'll need a dit. You can see examples in [tests/dits](https://github.com/isaiahshiner/dit-cli/tree/master/tests/dits).

Let's make a simple dit, `name.dit`:

```
Name {
    String value;
}
```

This is a dit class, with a single contained (instance) variable. String is the only primitive type. Everything is either a string, object, or list.

Now that we have a class, we can make an object and assign it.

```
Name name;
name.value = 'John';
```

Great! Now we can get the stored name by querying the file:

    dit query name.dit '@@name.value'
    "John"

The double at symbol `@@` is the dit escape sequence, used to reference variables in code and query strings. Variables are always referenced as `.` operations.

We can ask for the entire `name` object, rather than a specific part:

    dit query name.dit '@@name'
    {"class":"Name","value":"John"}

This will serialize the object. The default serialization language is Javascript, which means JSON, but this is highly configurable. We would rather a `Name` object be represented by it's value. Let's add a print function for that:

```
Name {
    String value;
    print value;
}
```

    dit query name.dit '@@print(name)'
    "John"

`print()` will try to use a print function before serializing. It will always return a useful value, never `null`/`None`.

But we have a problem: There's nothing to stop something like this:

    dit query name.dit '@@print(name)'
    "4jZw3ef\n"

We need to make sure it's really a name. Let's add a validator!

```
Name {
    String value;
    print value;
    validator Javascript {{
        // This is real Javascript (nodejs)
        let name = @@value;
        if (!/^[A-Z][A-z]+$/.test(name)) {
            return `Not a valid name: "${name}"`
        }
        return true;
    }}
}
```

Dit will interpret everything in the double brace `{{}}` section as Javascript code, and use it to build a .js file. `@@value` will be converted into a JS compatible string before running the code. You can see all the language configurations in ~/.dit-languages. This is how new languages will be added and customized.

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
        # Python and Javascript are supported out of the box
        full = @@givenName
        for mid in @@middleNames: # Returns a list of Python dictionaries
            full += ' ' + mid
        full += ' ' + @@familyName
        return full
    }}
}
```

A full name contains several Name objects. `middleNames` is a list, since people can have multiple middle names. Note that a list can be any shape of list: 2D, 3D, jagged, etc, they're all just `list ClassName varName`;

The print script nicely puts everything together. There's not really any need for a validator, since all the `Names` will be validated before ever reaching this class.

For assigning a `FullName` object, we still have the `name` variable from before, but we don't want to manually create a different variable for each object.

```
Name firstName;
Name middleName1;
Name middleName2;
```

So, we can use an assigner, which will create an anonymous object for us. Assigners are somewhere in between a constructor and a function. They can only have assignment statements currently, but they will probably look more like arbitrary functions in the future, with scripts to validate and transform parameters before assignment. You could have a large object defined by a single JSON, just by peeling it apart and assigning values. Then print it back as a JSON, JSON in a different schema, XML, CSV... ah, but I digress.

```
// It's okay for assigners to have single letter names.
Name n(nameParam) {
    value = nameParam;
    // We could have more parameters and assignments if needed
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
    dit query name.dit '@@myName' | python -m json.tool > output.json
    cat output.json
    {
        "class": "FullName",
        "print": "Hi! My name is Isaiah Leopold Koser Shiner",
        "givenName": {
            "class": "Name",
            "print": "Isaiah",
            "value": "Isaiah"
        },
        "middleNames": [
            {
                "class": "Name",
                "print": "Leopold",
                "value": "Leopold"
            },
            {
                "class": "Name",
                "print": "Koser",
                "value": "Koser"
            }
        ],
        "familyName": {
            "class": "Name",
            "print": "Shiner",
            "value": "Shiner"
        }
    }


Finally, let's take a quick look at inheritance.

```
OtherName {
    extends Name;
    validator Python {{
        if @@value == 'Tom':
            return 'I don\'t like the name Tom."
        return True
    }}
}
```
Child classes have all the fields of their parents, so `value` exists in `OtherName` implicitly. All the `Names` are validated by the parent, then the child. Print functions must be explicitly inherited by type, like `print Name;`.


`extends` must be the first thing in a class, if it is to appear at all. To inherit from multiple classes, just separate with commas, like `extends Name, AndSomeOtherObject;`. If there are name conflicts, the first extended class takes precedence, then the second class must explicitly be called out:

```
C {
    extends A, B;
    print name; // gets name from A
    print B.name; // gets name from B
    // Remember that this is only if both A and B have a variable called 'name'
}
```

The real documentation is entirely WIP right now, so if you have questions, please don't hesitate to shoot me a message on [Discord](https://discord.gg/7shhUxy) or email me at isaiah@ditabase.io. You can also make issues on the [issues tracker.](https://github.com/isaiahshiner/dit-cli/issues)

## Why? What's the point?

The long answer is written [here.](https://github.com/isaiahshiner/dit-cli/blob/master/docs/whats-the-point.md)

The short answer is that there's nothing out there that does everything.

* You can write your own custom validation code for each project, each situation, but that is a huge violation of [DRY](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself). Not that *you're* repeating yourself, but that everyone else is repeating each other.
  
* Schema.org has a wonderful set of schemas, for almost every situation imaginable, but that's all they are, just schemas. I know where I would start if I were laying out a [Person Schema](https://schema.org/Person), but validation is still my problem. And furthermore, Schema.org is a relatively closed system. I can't just whip up a child of another schema if I want to, the way I can with dit.

* JSON-Schema, JSON-LD, IPLD, all suffer from the general problem that they choose a specific way to implement things, which makes them wonderful, but not universal. Dit is [not trying to replace](https://xkcd.com/927/) every other way to write down data, only be a bridge between them. Dit relies heavily on JSON because it's so good, but in the edge cases, you can use CSV, or something else custom. Even if one format can cover 60%, the network effect of including the other 40% is incredibly valuable.

We need the validation, schemas, formatting, and even the discussion and community to all be in one place. The end game is to have a repository of open source dit classes, so that any data from any context can be used in any other context. I hope you agree, and you'll consider trying dit.

## Links
* [Official Website](https://www.ditabase.io/)

* [Discord Chat](https://discord.gg/7shhUxy)

* isaiah@ditabase.io

* [Issue Tracker](https://github.com/isaiahshiner/dit-cli/issues)