# What's the point of dit?

To understand this, we need to forget about dit, about DitaBase, about schemas, objects and the whole mess of specifics and talk about one central idea:

Data could be better. A *lot* better. To explain, I'm going to introduce a concept I'm calling **perfect data.**

Imagine the world in the year 2200. All the data just works, right? Doesn't matter the specifics, nuances, or whatever, it all just works together, seamlessly. It would be pretty embarrassing if your automated flying car couldn't play your music because it was in the wrong format. A Starfleet Officer asks the ships computer something, and it doesn't say "I can't answer that because JSON and spreadsheets don't work together." How else can you describe the data in that world other than "perfect"?

To be a little more specific, we're going to need some definitions:
* Data: Any kind of information anywhere in any situation. No limitations.

* Intersection: Two pieces of data have some information that is effectively the same. How are a book and a tax return document related? The book has an author, and tax returns are for a specific person. They intersect at "person".

* Queryable: Searching for something would yield the correct data in a format that could be used. I need to be able to check if the author of the book and the owner of the tax return are actually the same person. Spreadsheets are queryable, PDFs are not. Note that these interactions must be automated. Even if a human could easily discern the correct answer, or activate a script that could, it must happen without a human ever knowing the script was even necessary.

* Congruent: Two pieces of data for which all intersections are queryable.

* Perfect: A subset of data for which the congruency is higher than say, 75%.

For example:

    "Name": "John Doe"

vs.

    "Name": {
        "FirstName": "John",
        "LastName": "Doe"
    }`

This data is clearly not congruent, even though the same information is conveyed. Tedious issues like `Name` vs. `name`, or `Street` vs. `St.` also break congruency.

The perfectness of a set of data can be expressed by taking two random pieces of data, (database queries, records, documents, emails, anything) and checking them for congruency. Add another random piece of data and check against all the previous. Divide the number of congruent connections by the total connections and repeat until it converges. Thats your perfection percentage.

If we checked the perfection of a single company, let's say FedEx, their perfection might be around 40%, since they have at least 1 very large validated database. All the stuff from there would be congruent, and probably nothing else would be. Data in just the USA would probably be more perfect than say, India.

But what about global perfect data? Yes, all the data in the world, all of it one one giant pile, pull out two pieces and try to compare them. I would guess the perfection is less than 1%.

The stated goal of DitaBase is to get global data perfection above by 70% by 2030.

// This document is incomplete, more to follow.