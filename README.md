# dit - The universal container file
Dit is a new container file, intended to be the "One File to Rule Them All". It's a cross between a data storage file and a scripting language, with features to handle every use case for managing data. Dit files can transport data across different formats and platforms, so sharing data is much easier.

## Install and Usage

    pip install dit-cli

Install dit with [pip for python](https://pip.pypa.io/en/stable/installing/). Note that you will need Python 3.8 and an installation of any guest languages you want to use, such as NodeJS, Lua, etc.

    dit -h, -v [filename]

    -h     : display help
    -v     : display version

Dit runs just like any source file: `dit someFile.dit`

## Dit Tutorial
An example of all dit features can be found in [examples/Tutorial.dit](https://github.com/ditabase/dit-cli/blob/master/examples/Tutorial.dit). Note that dit is a work in progress, and many more features are planned. You can see a rough roadmap [here](https://github.com/ditabase/dit-cli/blob/master/docs/FeatureRoadMap.md). If you have questions, please don't hesitate to shoot me a message on [Discord](https://discord.gg/7shhUxy) or email me at isaiah@ditabase.io.

## Kirby Langs
Let's go over the most significant new feature in dit, and how it can rule other languages without succumbing to [XKCD 927](https://xkcd.com/927/): KirbyLang Functions. A KirbyLang is a new term for any language that can easily absorb the properties of any other language, just like Kirby, the Nintendo character.

![Kirby sucking up food](https://github.com/ditabase/dit-cli/blob/functions/docs/gifs/kirby.gif)

Imagine Kirby sucking up other languages and technologies, really really fast.

A KirbyLang can go about managing the Guest languages however it wants to. Dit is just one implementation, and there may be better ones. However, all KirbyLangs must meet the following requirements.

- Adding a new language must be "easy". It should require less than 1000 lines of code, and take less than 100 man hours.
- All Functions must be Kirbyish. That is, they act exactly like the normal functions in the KirbyLang, with no loss in functionality.

For dit, a guest language is added by implementing a local socket server in that language. Dit will send a job to the socket server with the filepath of some code it needs the guest to run. The guest has to run it and return the results back to dit.

Adding Lua took me about 12 hours and 76 lines, even though I was rusty and had never used sockets or JSON in Lua. I am sure compiled languages will be more complex, maybe 2 or 4 fold, but that's okay. You can see how languages are implemented [here](https://github.com/ditabase/dits/blob/master/langs/commonLangs.dit).

## Shape Expressions
Dit currently communicates between the Guest langs and Dit using Shape Expressions. These are a little confusing, so let's go over them. Here's a simple "Hello World" function in dit syntax.

```
func SayHello() {|
    print("Hello World!");
|}
```

 Now, lets see this in JavaScript.

```
sig JavaScript func SayHello() {|
    <|print("Hello World!")|>
|}
```

What you see is called a *triangle expression*. It uses `<|` and `|>` as its braces, since they won't conflict with GuestLangs. Everything within the triangle expression is executed as dit code. This allows a GuestLang to use it's flow control. Now let's see a slightly more complicated function, which should be fairly self-explanatory.

```
sig JavaScript Bool func isEven(Num n) {|
    if (<|n|> % 2 == 0) {      // JS doesn't know what n is, dit will send it to us.
        <|return true|>        // dit understands all JSON types
    }
    else {
        <|return false|>
    }
|}
```

One more, this time in Python, just to keep you on your toes. This code is going to look very odd at first, but it's not too hard to follow.

```
sig Python Num func lowestValue(listOf Num nums) {|
    <|return (|min(<|nums|>)|)|>
|}
```

Here we have a *circle expression* within a triangle. Circle expressions allow use of the GuestLang again, for sending data back to dit. There is another triangle for getting the `nums` array into the `min` function. Shape expressions can be nested infinitely, if you need to.

Review:
- Triangle expression: Pull info from dit, execute dit commands.
- Circle expression: Send info back to dit, arguments for dit commands.

The purpose of this syntax is to be as generic as possible, and allow near normal use of any GuestLang. Converting code to dit is just wrapping the function differently and adding the correct shape expressions. There are no libraries or other things that would require rewriting a function entirely. However, this syntax is still subject to change, so if you have ideas, let me know! Also remember the complete tutorial is [here](https://github.com/ditabase/dit-cli/blob/master/examples/Tutorial.dit), KirbyLangs are the only thing I'm going over for now.

## Why? What's the point of this?

The long answer is written [here.](https://github.com/isaiahshiner/dit-cli/blob/master/docs/whats-the-point.md)

The short answer is that there's nothing out there that does everything.

* You can write your own custom validation code for each project, each situation, but that is a huge violation of [DRY](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself). Not that *you* are repeating yourself, but that everyone else is repeating each other.
  
* Schema.org has a wonderful set of schemas, for almost every situation imaginable, but that's all they are, just schemas. I know where I would start if I were laying out a [Person Schema](https://schema.org/Person), but validation is still my problem. And furthermore, Schema.org is a relatively closed system. I can't just whip up another child class, the way I can with dit.

* JSON-Schema, JSON-LD, IPLD, all suffer from the general problem that they choose a specific way to implement things, which makes them wonderful, but not universal. Dit is [not trying to replace](https://xkcd.com/927/) every other way to write down data, only be a bridge between them. Dit relies heavily on JSON because it's so good, but in the edge cases, you can use CSV, or something else custom. Even if one format can cover 60%, the network effect of including the other 40% is incredibly valuable.

We need the validation, schemas, formatting, and even the discussion and community to all be in one place. The end game is to have a repository of open source dit classes, so that any data from any context can be used in any other context. I hope you agree, and you'll consider trying dit.

## Links
* [Official Website](https://www.ditabase.io/)

* [Discord Chat](https://discord.gg/7shhUxy)

* isaiah@ditabase.io

* [Issue Tracker](https://github.com/isaiahshiner/dit-cli/issues)
