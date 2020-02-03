# What's the point of dit?

To understand this, we need to forget about dit, about DitaBase, about schemas, objects and the whole mess of specifics and talk about one central idea.

Data could be a lot better. A *lot* better. Magnitudes better.

To explain, I'm going to introduce a concept I'm calling **perfect data.** Data is perfect when its structure is queryable with any other data of it's type, automatically. If you have to open Excel or do any processing, it's not perfect. And of course if the data has actual errors, that isn't perfect either.

The perfectness of a set of data can be expressed by taking a random piece of data from the set, and comparing it to another random piece of data. If the two pieces are instantly and automatically queryable with each other, they are perfect. 

For example:

    "Name": "John Doe"

vs.

    "Name": {
        "FirstName": "John",
        "LastName": "Doe"
    }`

is clearly not perfect, even though the same information is conveyed.

Even tedious issues like `Name` vs. `name` would break data perfection.

You could match them up fairly easily, but any manual processing doesn't count. You will see why later.