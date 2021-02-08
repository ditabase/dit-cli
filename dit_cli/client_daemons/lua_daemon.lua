local json = require("rxi-json-lua")
local socket = require("socket")
tcp = assert(socket.tcp())
local host, port = "127.0.0.1", arg[1]
package.path = '/tmp/dit/?.lua;' .. package.path
tcp:connect(host, port);
local connectMes = json.encode({type = "connect", lang = "Lua"})
tcp:send(connectMes)

EXE_COROUTINE = nil

local function daemon_loop()
    local s, status, partial = tcp:receive()
    if status ~= "closed" then
        jsonData = json.decode(s)
        local coroutine_param = nil
        if jsonData['type'] == "call_func" then
            coroutine_param = require(string.sub(jsonData["func_path"], 10, -5))
            EXE_COROUTINE = coroutine.create(function (func_to_call)
                    func_to_call()
                end)
        elseif jsonData['type'] == "ditlang_callback" then
            coroutine_param = jsonData["result"]
        end

        local no_errors, exe_ditlang = coroutine.resume(EXE_COROUTINE, coroutine_param)
        if exe_ditlang == 0 then
            local finish_message = json.encode({type = "finish_func"})
            tcp:send(finish_message)
        else
            exeMessage = json.encode({type = "exe_ditlang", result = exe_ditlang})
            tcp:send(exeMessage)
        end
    end
end

while true do
    local status, err = pcall(daemon_loop) 
    if status == false then
        crashMessage = json.encode({type = "crash", result = err})
        tcp:send(crashMessage)
    end
end
tcp:close()