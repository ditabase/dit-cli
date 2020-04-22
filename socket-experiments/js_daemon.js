const net = require('net')
const START = + new Date();

const server = new net.Socket();
server.connect('5500', '127.0.0.1', () => {
    start_mes = JSON.stringify({ "stamp": START, "lang": "Javascript" });
    server.write(start_mes);
});
server.on('data', (data) => {
    var chunk = data.toString();
    if (chunk == 'CLOSE_CONNECTION') {
        server.destroy();
        return
    }
    var script = require(chunk);

    var start = + new Date();
    var start_mes = JSON.stringify({ "stamp": start, "type": "start" });
    server.write(start_mes);

    var result = script.run();
    result.then((data) => {
        var finish = + new Date();
        var job_mes = JSON.stringify({ "stamp": finish, "type": "finish", "result": data });
        server.write(job_mes);
    });

});