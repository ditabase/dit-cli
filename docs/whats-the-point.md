# What's the point of dit?

Dit is a solution to a problem. A big problem, but one that doesn't obviously exist. To make sense of it, we need to forget about dit and all the specifics and talk about one central concept:

Data could be better. A *lot* better. Magnitudes better.

Imagine the world 200 years from now. All the data just works, right? Doesn't matter the specifics, nuances, or details, it all just works together, seamlessly. It would be pretty embarrassing if your automated flying car couldn't play your music because it was in the wrong format. A Starfleet Officer asks the ship's computer something, and it doesn't say "I can't answer that because JSON and spreadsheets don't work together." How else can you describe the data in that world other than "perfect"?

And this is the problem. Data needs to be perfect, and it's not. The reason this problem isn't obvious is because it's so hard to imagine that there could be a solution. Which is why we have tons of industry specific, end-to-end solutions. The point of dit is to be the totally general purpose solution.

## Definitions
"Perfect" is an accurate name, but its fairly vague. Let me be a little clearer about what I mean:
* Data: Any kind of information anywhere in any situation. No limitations.

* Intersection: Two pieces of data have some information about the same concept. How are a book and a tax return document related? The book has an author, and tax returns are for a specific person. They intersect at "person". A flashlight and a keychain are both physical objects, and are made of materials which might be similar, such as steel and nylon. But what grade of steel? What type of nylon? All of these are intersections.

* Queryable: Searching for something would yield the correct data in a format that could be used. I need to be able to check if the author of the book and the owner of the tax return are actually the same person. Spreadsheets are queryable, PDFs are not. Note that these interactions must be automated. Even if a human could easily discern the correct answer, or activate a script that could, it must happen without a human ever knowing the script was even necessary.

* Congruent: Two pieces of data for which all intersections are queryable.

* Perfection: The percentage of congruent data in a subset.

* Perfect: The perfection of a set of data is high, above say, 70%.

For example:

    "Name": "John Doe"

vs.

    "Name": {
        "FirstName": "John",
        "LastName": "Doe"
    }

This data is clearly not queryable, even though the same information is conveyed. Tedious issues like `Name` vs. `name`, or `Street` vs. `St.` also break querying.

The perfectness of a set of data can be expressed by taking two random pieces of data, (database queries, records, documents, emails, anything) and checking them for congruency. Add another random piece of data and check against all the previous. Divide the number of congruent connections by the total connections and repeat until it stays consistent. That's your perfection percentage.

If we checked the perfection of a single company, let's say FedEx, their perfection might be around 40%, since they have at least 1 very large validated database. All the stuff from there would be congruent, and probably nothing else would be. Data in just the USA would probably be more perfect than say, India.

But what about global perfect data? Yes, all the data in the world, all of it one one giant pile, pull out two pieces and try to compare them. I would guess the perfection is less than 1%. The stated goal of DitaBase is to get **global data perfection above 70% by 2030**. This would fundamentally change the way humanity interacts with data, disrupting every single industry in one way or another.

# Use cases

Dit will eventually be applied everywhere, but let's look at some specific examples.

### Ecommerce
Products on ecommerce sites require an enormous amount of data. Each platform requires data in a different format, and mistakes in data are only revealed after exporting and uploading data. Kitchen sink sites like Amazon can't ask for all the specific data about a product because there are just to many fields to manage, which leads to an entire genre of websites that just allow searching for products, not selling. With Dit, all of these problems would go away. Once accurate data is produced, it can easily be moved to any platform, automatically, with no loss in specificity.

### Search
Ecommerce is just a microcosm of the greater problem with search: Google doesn't actually know anything. They don't know the answer to your question, so they offer websites which have statistics that imply that the website knows the answer. Don't get me wrong, Google is wonderful, but we can do so much better. With dit, we can make a search engine that actually does know the real answer to your question. It can pull results from any dit compatible public database, and order them for you, perform calculations, or generate graphs. Scientific data can be published in a ready queryable format, allowing anyone to draw conclusions from their research, without knowing anything about the exact source of the data. Massive amounts of statistical data can be accessed by consumers to answer complex questions without knowing anything about how complex they are.

### Automation
Ultimately, better data is essentially a tool to allow more value to be created with less human input. With perfect data, it becomes reasonable to start talking about automating large parts of the global economy. Factory machines can begin communicating with each other without explicit coding, since they all speak the same language: dit. A machine could offer an `AvailableActions` object, which describes a generic API for how the machine can be used, and another machine could easily take advantage of this, regardless of the specific manufacturer of either machine.

If blockchain and cryptocurrency come to fruition, this automation can apply directly to the economy. A pseudo-intelligent logistics program could request a mechanical part, offering only the dit object describing problem to be solved, and a price in Bitcoin for completion of service. The blockchain network would automatically relay this information to a freelancing human engineer, an automated manufacturer, and an automated delivery network. Very few humans would ever required during this process, since all the unrelated machines communicate seamlessly via dit objects, without needing any explicit prior knowledge of the other machines. The finished part would arrive, with penalties in Bitcoin if it doesn't 

This level of total automation requires an lot of different technologies to work. But certainly, without perfect data, or some other entirely generic language for the machines to communicate with, it could never work.

# Why now?

Has Perfect Data been possible for a long time? Has it been tried before? What has changed? Realistically, perfect data as an idea is probably as old as computers, going all the way back the [Vannevar Bush and the Memex.](https://en.wikipedia.org/wiki/Memex) The basic idea of the internet was "The information superhighway". HTTP, the sematic web, and then recently Schema.org were incremental steps leading towards perfect data. It has always been a problem that needed a solution, and every step of internet infrastructure was basically an attempt to move closer to it.

The problem with all of those attempts is that they simply haven't been in a place to propose a system of the scale and specificity required. It was always much more reasonable to propose smaller scale, incremental improvements (not that HTTP was necessarily incremental). Inventions in recent years have attacked true perfect data, but only a subset. JSON-Schema is a wonderful in-file validator, but only for JSON. The semantic web has continued to add new syntaxes like JSON-LD, but they have yet to propose anything generic, the way dit is. [Interplanetary Linked Data](https://ipld.io/) is similar to dit in some ways, but the supported content is not fully generic, and it's tied directly to the blockchain.

IPLD represents the problem with all existing solutions: they're great, if you want to solve a smaller, specific problem, rather than the entire problem at once. You can't just replace all of these great solutions with some kind of [God format](https://xkcd.com/927/), that would be impossible. Real perfect data requires every one of these smaller solutions continue to exist, but connected. Dit does not *replace* any of these, only creates a bridge between them. However, a general purpose solution would be a waste of time if none of these smaller, pseudo-general solutions already existed. The work for dit to do would be too extreme. You can't bridge between mainlands that don't exist.

Another change that has made perfect data more viable in the the cost of technology reaching a necessary minimum. There is almost no digital consumer device worth producing today that is incapable of running a striped down version of Linux. That means that anything capable of processing data is capable of using a solution like dit. This is the same change that made the Internet of Things possible: anything with a microprocessor can now connect to the internet. You could never expect dit to work in general without being able to run Linux on almost anything, but since around 2015, you basically can, since a microprocessor doesn't cost more than $5-15 retail.

The lack of perfect data is also the reason these IoT devices suck. Networked devices only have value proportional to the number of other devices they can connect to. Without a universal language, most devices can't talk to each other unless they are made by the same manufacturer, or use one of the many "standard" IoT protocols. There aren't a lot of useful features for an IoT toaster, but if every digital device in your entire life was connected, it would seem strange that your toaster wasn't.

All in all, I would guess that a totally general perfect data system could have been attempted as early as 2012, when smartphones really started to get good (Schema.org was started in 2011). With every passing year, the number of people with problems that need perfect data as a solution increases. By 2025, most countries that we, in the rich world, previously thought of as "developing" will have fully joined the modern internet based economy, and will all bring their own demands for data usage. If there isn't a perfect data solution by then, the world will be desperately clambering for it.

But dit will take time to make. Even starting now, it will still be a race to have global acceptance and appeal by 2025. Every single tiny variation in data needs explicit code to accommodate it, written by the experts in each field, since no one else will know every variation. At that point, dit will only be mainstream, and getting the laggards adopted will be a monumental struggle, which is why the target is only for 70% perfect data by the end of the decade.