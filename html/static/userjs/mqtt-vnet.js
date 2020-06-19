/*******************************************************************************
 * Copyright (c) 2015 IBM Corp.
 *
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * and Eclipse Distribution License v1.0 which accompany this distribution.
 *
 * The Eclipse Public License is available at
 *    http://www.eclipse.org/legal/epl-v10.html
 * and the Eclipse Distribution License is available at
 *   http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * Contributors:
 *    James Sutton - Initial Contribution
 *******************************************************************************/

/*
Eclipse Paho MQTT-JS Utility
This utility can be used to test the Eclipse Paho MQTT Javascript client.
*/

// Create a client instance
mqtt_client = null;
mqttc_connected = false;
var current_opcconfig = new Object();
var mqtt_host = window.location.hostname;
var mqtt_port = 3884;
var clientId = "webclient-" + makeid();
var received_logs_num = 0;


/**
 *    临时兼容IE，去掉可变参数
 */
function logMessage(type, content) {
    if (type === "INFO") {
        console.info(content);
    } else if (type === "ERROR") {
        console.error(content);
    } else {
        console.log(content);
    }
}

/**
 *    日志处理
 */
// function logMessage(type, ...content) {
//     if (type === "INFO") {
//         console.info(...content);
//     } else if (type === "ERROR") {
//         console.error(...content);
//     } else {
//         console.log(...content);
//     }
// }

function makeid() {
    var text = "";
    var possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    for (var i = 0; i < 8; i++)
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    return text;
}

// logMessage("INFO", "Starting Eclipse Paho JavaScript Utility.");
// Things to do as soon as the page loads
// document.getElementById("clientIdInput").value = "js-utility-" + makeid();

// called when the client connects
function onConnect(context) {
    // Once a connection has been made, make a subscription and send a message.
    var connectionString = context.invocationContext.host + ":" + context.invocationContext.port + context.invocationContext.path;
    console.log("Connection Success ", "URI: ", connectionString, ", ID: ", context.invocationContext.clientId);
    // logMessage("INFO", "Connection Success ", "[URI: ", connectionString, ", ID: ", context.invocationContext.clientId, "]");
    // var statusSpan = document.getElementById("connectionStatus");
    // statusSpan.innerHTML = "Connected to: " + connectionString + " as " + context.invocationContext.clientId;
    mqttc_connected = false;

}

function onConnected(reconnect = false, uri) {
    // Once a connection has been made, make a subscription and send a message.
    //   logMessage("INFO", "Client Has now connected: [Reconnected: ", reconnect, ", URI: ", uri, "]");
    console.log("Client Has now connected. Reconnected: ", reconnect, ", URI: ", uri);
    mqttc_connected = true;
    mqtt_client.subscribe(['v1/common/api/RESULT', 'v1/vnet/api/RESULT', 'VNET/STATUS/#']);

    // var message = new Paho.Message(JSON.stringify({"id":'getConfig/' + $("#newClientID").val() + '/' + Date.parse(new Date()).toString()}));
    // message.destinationName = 'v1/opcdabrg/api/getConfig';
    // message.qos = 0;
    // mqtt_client.send(message);
    // var message = new Paho.Message(JSON.stringify({"id":'getsysconfig/' + $("#newClientID").val() + '/' + Date.parse(new Date()).toString()}));
    // message.destinationName = 'v1/opcdabrg/api/getsysconfig';
    // message.qos = 0;
    // mqtt_client.send(message);
}

function onFail(context) {
    console.log("Failed to connect. [Error Message: ", context.errorMessage);
    // logMessage("ERROR", "Failed to connect. [Error Message: ", context.errorMessage, "]");
    // var statusSpan = document.getElementById("connectionStatus");
    // statusSpan.innerHTML = "Failed to connect: " + context.errorMessage;
    mqttc_connected = false;
}

// called when the client loses its connection
function onConnectionLost(responseObject) {
    if (responseObject.errorCode !== 0) {
        console.log("Connection Lost. Error Message: ", responseObject.errorMessage);
        // logMessage("INFO", "Connection Lost. [Error Message: ", responseObject.errorMessage, "]");
    }
    mqttc_connected = false;
}

// called when a message arrives
function onMessageArrived(message) {
    // console.log("topic: ",message.destinationName);
    var arr_topic = message.destinationName.split("/");
    // console.log(arr_topic);
    // logMessage("INFO", "Message Recieved: [Topic: ", message.destinationName, ", Payload: ", message.payloadString, ", QoS: ", message.qos, ", Retained: ", message.retained, ", Duplicate: ", message.duplicate, "]");
    //--------------------------接收本地后台发布的状态信息--------------------------------------
    if (arr_topic[1] === "STATUS") {
        // console.log(message.payloadString);
        var data_message = JSON.parse(message.payloadString);
        if (!$.isEmptyObject(data_message)) {
            set_notice_info(data_message);
            vnetStatusOBJ = data_message;
            if (data_message.hasOwnProperty('vnet_is_running')) {
                vnet_is_running = data_message.vnet_is_running
            }
        }
        if (gatevnet_ready) {
            if (vnet_is_running) {
                $("span.gate_status").text(data_message.gate_online);
                $('span.start_vnet').addClass('mdui-color-grey');
                $('span.start_vnet').removeClass('mdui-color-green');
                $('span.stop_vnet').removeClass('mdui-color-grey');
                $('span.stop_vnet').addClass('mdui-color-red');
            } else {
                $('span.start_vnet').removeClass('mdui-color-grey');
                $('span.start_vnet').addClass('mdui-color-green');
                $('span.stop_vnet').addClass('mdui-color-grey');
                $('span.stop_vnet').removeClass('mdui-color-red');
            }
        }
    }
    //--------------------------接收本地后台发布的通知信息--------------------------------------
    if (arr_topic[1] === "NOTIFY") {
        // console.log(message.payloadString);
        var notice_message = JSON.parse(message.payloadString);
        set_notice_info(notice_message);

    }
    //--------------------------接收本地后台返回的API信息--------------------------------------
    if (arr_topic[3] === "RESULT") {
        console.log(arr_topic);
        // console.log(message.payloadString);
        var apiResult_message = JSON.parse(message.payloadString);
        if (apiResult_message.result) {
            // var local_datetime = new Date(parseInt(new Date().getTime())).toLocaleString('chinese', { hour12: false });
        }
        //--------------------------页面设置保存到本地 返回--------------------------------------
        if (apiResult_message['id'].indexOf("common/save") != -1) {
            set_api_result(apiResult_message);
        }
        //--------------------------删除本地保存的配置 返回--------------------------------------
        if (apiResult_message['id'].indexOf("common/remove") != -1) {
            set_api_result(apiResult_message);
        }
        //--------------------------加载本地保存的配置到页面 返回--------------------------------------
        if (apiResult_message['id'].indexOf("common/load") != -1) {
            set_api_result(apiResult_message);
            if (apiResult_message.result) {
                var config = apiResult_message.data;
                if (!$.isEmptyObject(config)) {
                    if (config.gate) {
                        $("span.dest_sn").text(config.gate);
                    }
                    if (config.npshost) {
                        $("input[name='npsHost']").val(config.npshost);
                    }
                    if (config.npsuser) {
                        $("input[name='npsUser']").val(config.npsuser);
                    }
                    if (config.auth_code) {
                        $("input[name='accesskey']").val(config.auth_code);
                    }
                    if (config.gate && config.npshost && config.npsuser && config.auth_code) {
                        setTimeout(function () {
                            get_gatevnet_ready();
                        }, 1000);
                    }
                }
            }
        }
        //-----------------------------获取当前用户在线的网关 返回-----------------------------------
        if (apiResult_message['id'].indexOf("common/gatelist") != -1) {
            if (apiResult_message.result) {
                var gates = apiResult_message.data;
                var gatelist_table = $("table.gatelist_table tbody")
                if (!$.isEmptyObject(gates)) {
                    creat_gatelist_table(gates, gatelist_table)
                }
            } else {
                set_api_result(apiResult_message);
            }
        }
        //-------------------------------检测选中网关的Vnet环境 返回---------------------------------
        if (apiResult_message['id'].indexOf("vnet/ready") != -1) {
            // console.log(apiResult_message.data);
            set_api_result(apiResult_message);
            $("span.gate_status").text("ONLINE");
            $("span.local_ready").text("OK");
            if (apiResult_message.result) {
                if (apiResult_message.data.ready) {
                    $("span.gate_ready").html("");
                    $("span.gate_ready").text("OK");
                    gatevnet_ready = true;
                    if (!vnet_is_running) {
                        $('span.start_vnet').removeClass('mdui-color-grey');
                        $('span.start_vnet').addClass('mdui-color-green');
                    }
                } else {
                    var appinfo = apiResult_message.data.info;
                    var content = "";
                    var action = "";
                    if ($.isEmptyObject(appinfo)) {
                        content = "网关中Vnet应用未安装";
                        action = "install";
                    } else {
                        if (appinfo.name !== "APP00000379") {
                            content = "网关中Vnet应用需要升级";
                            action = "upgrade";
                        } else {
                            content = "网关中Vnet应用未启动";
                            action = "start";
                        }
                    }
                    var html = "<button type=\"button\" class=\"mdui-btn  mdui-btn-icon gate_fix\"><i class=\"mdui-icon material-icons\">build</i></button>"
                    $("span.gate_ready").html(html);
                    $('button.gate_fix').click(function () {
                        mdui.dialog({
                            title: '详情',
                            modal: true,
                            content: content,
                            buttons: [
                                {
                                    text: '关闭'
                                },
                                {
                                    text: '修复',
                                    onClick: function (inst) {
                                        mdui.snackbar({
                                            message: '修复网关Vnet环境！'
                                        });
                                        if (mqttc_connected) {
                                            console.log('修复网关Vnet环境');
                                            var gate_sn = $("span.dest_sn").text();
                                            var auth_code = $("input[name='accesskey']").val();
                                            if (gate_sn !== '') {
                                                var message = new Paho.Message(JSON.stringify({
                                                    "id": 'vnet/action/' + clientId + '/' + Date.parse(new Date()).toString(),
                                                    "gate": gate_sn,
                                                    "action": action,
                                                    "auth_code": auth_code
                                                }));
                                                message.destinationName = 'v1/vnet/api/action';
                                                message.qos = 0;
                                                mqtt_client.send(message);
                                            }

                                        }
                                    }
                                }
                            ]
                        });
                    });
                    gatevnet_ready = false;
                    if (!vnet_is_running) {
                        $('span.start_vnet').addClass('mdui-color-grey');
                        $('span.start_vnet').removeClass('mdui-color-green');
                    }
                }
            }

        }
        //----------------------------根据检测反馈修复网关Vnet 返回------------------------------------
        if (apiResult_message['id'].indexOf("vnet/action") != -1) {
            set_api_result(apiResult_message);
            mdui.snackbar({
                message: '修复完毕，再次检测网关Vnet环境！'
            });
            get_gatevnet_ready();
        }
        //-----------------------------启动Vnet 返回-----------------------------------
        if (apiResult_message['id'].indexOf("vnet/start") != -1) {
            in_start_action = false;
            set_api_result(apiResult_message);
            if (apiResult_message.result) {
                vnet_is_running = true;
            }


        }
        //----------------------------停止Vnet 返回------------------------------------
        if (apiResult_message['id'].indexOf("vnet/stop") != -1) {
            in_stop_action = false;
            set_api_result(apiResult_message);
            if (apiResult_message.result) {
                vnet_is_running = false;
            }


        }
        //------------------------------保持Vnet心跳 返回----------------------------------
        if (apiResult_message['id'].indexOf("vnet/ping") != -1) {
            // set_api_result(apiResult_message);
        }
        //----------------------------------------------------------------

    }

}

function connectionToggle() {
    if (mqttc_connected) {
        disconnect();
        $('button.mqtt-connect-btn').html('<i class="mdui-icon material-icons">highlight</i>')
    } else {
        connect();
    }
}

function connect() {
    var hostname = mqtt_host;
    var port = mqtt_port

    var path = "/ws";
    var user = 'viccom';
    var pass = 'Pa88word';
    var keepAlive = 60;
    var timeout = 3;
    var tls = false;
    var autoReconnect = false;
    var cleanSession = true;
    var lastWillTopic = null;
    var lastWillQos = 0;
    var lastWillRetain = false;
    var lastWillMessage = null;


    if (path.length > 0) {
        mqtt_client = new Paho.Client(hostname, Number(port), path, clientId);
    } else {
        mqtt_client = new Paho.Client(hostname, Number(port), clientId);
    }
    // logMessage("INFO", "Connecting to Server: [Host: ", hostname, ", Port: ", port, ", Path: ", mqtt_client.path, ", ID: ", clientId, ", USER: ", user,", PASS: ", pass,"]");

    // set callback handlers
    mqtt_client.onConnectionLost = onConnectionLost;
    mqtt_client.onMessageArrived = onMessageArrived;
    mqtt_client.onConnected = onConnected;


    var options = {
        invocationContext: {host: hostname, port: port, path: mqtt_client.path, clientId: clientId},
        timeout: timeout,
        keepAliveInterval: keepAlive,
        cleanSession: cleanSession,
        useSSL: tls,
        reconnect: autoReconnect,
        onSuccess: onConnect,
        onFailure: onFail
    };
    if (user.length > 0) {
        options.userName = user;
    }
    if (pass.length > 0) {
        options.password = pass;
    }
    if (lastWillTopic) {
        var lastWillMessage = new Paho.Message(lastWillMessage);
        lastWillMessage.destinationName = lastWillTopic;
        lastWillMessage.qos = lastWillQos;
        lastWillMessage.retained = lastWillRetain;
        options.willMessage = lastWillMessage;
    }
    // connect the client
    try {
        mqtt_client.connect(options);
    } catch (error) {
        mqttc_connected = false;
        console.log(error);
    }
    // var statusSpan = document.getElementById("connectionStatus");
    // statusSpan.innerHTML = "Connecting...";
}

function disconnect() {
    // logMessage("INFO", "Disconnecting from Server.");
    console.log("Disconnecting from Server.");
    mqtt_client.disconnect();
    // var statusSpan = document.getElementById("connectionStatus");
    // statusSpan.innerHTML = "Connection - Disconnected.";
    mqttc_connected = false;
}
