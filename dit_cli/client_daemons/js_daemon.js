const net = require("net");
const server = new net.Socket();
const port = process.argv[2];
server.connect(port, "127.0.0.1", () => {
    server.write(JSON.stringify({ lang: "Javascript" }));
});

server.on("data", (data) => {
    var finalMessage = "finalMessage was not assigned";
    try {
        var script = require(data.toString());
        var result = script.run();
        finalMessage = JSON.stringify({ crash: false, result: result.toString() });
    } catch (err) {
        finalMessage = JSON.stringify({ crash: true, result: err.stack });
    } finally {
        server.write(finalMessage);
    }
});
