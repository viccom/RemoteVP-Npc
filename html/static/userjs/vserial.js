var vserialStatusOBJ = new Object();
var gatevserial_ready = false;
var vserial_is_running = false;
var in_start_action = false;
var in_stop_action = false;

//--------------------------周期检测和后台MQTT服务是否连接--------------------------------------
var mqtt_status_ret = setInterval(function () {
    if (mqttc_connected) {
        $('button.mqtt-connect-btn').html('<i class="mdui-icon material-icons mdui-color-green">highlight</i>')
    } else {
        $('button.mqtt-connect-btn').html('<i class="mdui-icon material-icons">highlight</i>');
        $('span.start_vserial').addClass('mdui-color-grey');
        $('span.start_vserial').removeClass('mdui-color-green');
    }
}, 1000);

//--------------------------Vnet运行时每20秒发送保持心跳--------------------------------------
var keep_alive_ret = setInterval(function () {
    if (mqttc_connected && vserial_is_running) {
        var message = new Paho.Message(JSON.stringify({"id": 'vserial/ping/' + clientId + '/' + Date.parse(new Date()).toString()}));
        message.destinationName = 'v1/vserial/api/ping';
        message.qos = 0;
        mqtt_client.send(message);
    }
}, 20000);

//--------------------------周期通过状态信息更改页面状态--------------------------------------
var vserial_ret = setInterval(function () {
    if (!$.isEmptyObject(vserialStatusOBJ)) {
        if (vserial_is_running) {
            var gate_sn = $("span.dest_sn").text();
            if (isEmpty(gate_sn)) {
                $("span.dest_sn").text(vserialStatusOBJ.info.gate);
                get_gatevserial_ready();
                $("input[name='npsHost']").val(vserialStatusOBJ.host);
                $("input[name='npsUser']").val(vserialStatusOBJ.info.user);
            }
            $("span.localvserialstatus").text(vserial_is_running);
            $("span.gatevserialstatus").text(vserialStatusOBJ.gate_npc_status);
            $("span.cloudclientstatus").text(vserialStatusOBJ.client_online);

            $("span.cloudclientinfo").text(vserialStatusOBJ.peer_state);
            if (!isEmpty(vserialStatusOBJ.gate_port_name)) {
                $("span.gatecom").text(vserialStatusOBJ.gate_port_name.toUpperCase());
            }
            $("span.localcom").text(vserialStatusOBJ.name);
            if (!$.isEmptyObject(vserialStatusOBJ.gate_com_params)) {
                $("span.gatecomParas").text("[" + vserialStatusOBJ.gate_com_params.baudrate.toString() + "/" + vserialStatusOBJ.gate_com_params.data_bits.toString() + "/" + vserialStatusOBJ.gate_com_params.parity.toString() + "/" + vserialStatusOBJ.gate_com_params.stop_bits.toString() + "]");
                $("span.localcomParas").text("[" + vserialStatusOBJ.BaudRate.toString() + "/" + vserialStatusOBJ.DataBits.toString() + "/" + vserialStatusOBJ.Parity.toString() + "/" + vserialStatusOBJ.StopBits.toString() + "]");

            }

            if (isEmpty(vserialStatusOBJ.app_path)) {
                $("span.localcomproc").text("");
                $("span.localcomstatus").text("关闭");
            } else {
                $("span.localcomstatus").text("打开");
                $("span.localcomproc").text(vserialStatusOBJ.app_path.toString());
            }
            $("span.localcom_recv").text(vserialStatusOBJ.recv_count);
            $("span.localcom_send").text(vserialStatusOBJ.send_count);
        } else {
            $("span.localvserialstatus").text(vserial_is_running);
            $("span.gatevserialstatus").text("UNKNOWN");
            $("span.cloudclientstatus").text("UNKNOWN");
            $("span.cloudclientinfo").text("UNKNOWN");
            $("span.gatecom").text("UNKNOWN");
            $("span.localcom").text("UNKNOWN");
            $("span.gatecomParas").text("")
            $("span.localcomParas").text("")
            $("span.localcomstatus").text("UNKNOWN");
            $("span.localcomproc").text("UNKNOWN");
            $("span.localcom_recv").text("UNKNOWN");
            $("span.localcom_send").text("UNKNOWN");
        }
    } else {
        $("span.localvserialstatus").text("UNKNOWN");
        $("span.gatevserialstatus").text("UNKNOWN");
        $("span.cloudclientstatus").text("UNKNOWN");
        $("span.cloudclientinfo").text("UNKNOWN");
        $("span.gatecom").text("UNKNOWN");
        $("span.localcom").text("UNKNOWN");
        $("span.gatecomParas").text("")
        $("span.localcomParas").text("")
        $("span.localcomstatus").text("UNKNOWN");
        $("span.localcomproc").text("UNKNOWN");
        $("span.localcom_recv").text("UNKNOWN");
        $("span.localcom_send").text("UNKNOWN");
    }

}, 2000);

/**
 *    get_user_gatelist
 */
function get_user_gatelist() {
    var user_accesskey = $.trim($("input[name='accesskey']").val());
    console.log(user_accesskey);
    if (isEmpty(user_accesskey)) {
        mdui.snackbar({
            message: '请输入用户授权信息！'
        });
        Panelinst.close('#item-1');
        return false;
    }
    // if(user_accesskey.length !== 36) {
    //     mdui.snackbar({
    //       message: '用户授权信息不正确！'
    //     });
    //     Panelinst.close('#item-1');
    //     return false;
    // }
    if (mqttc_connected) {
        console.log('查询当前用户gatelist');
        var message = new Paho.Message(JSON.stringify({
            "id": 'common/gatelist/' + clientId + '/' + Date.parse(new Date()).toString(),
            "auth_code": user_accesskey
        }));
        message.destinationName = 'v1/common/api/gatelist';
        message.qos = 0;
        mqtt_client.send(message);
    }
}

/**
 *    creat_gatelist_table
 */
function creat_gatelist_table(obj, tableobj) {
    var trhtml = '';
    $.each(obj, function (i, val) {
        trhtml = trhtml + '<tr data-id="' + val.device_sn + '" data-status="' + val.device_status + '">' +
            '<td>' + val.device_name + '</td>' +
            '<td>' + val.device_sn + '</td>' +
            '<td>' + val.device_status + '</td>' +
            '</tr>'

    })
    tableobj.empty();
    tableobj.append(trhtml);

    tableobj.on('click', 'tr', function () {
        if (vserial_is_running) {
            return false;
        }
        var gate_sn = $(this).data("id");
        $(this).addClass("mdui-table-row-selected");
        if (gate_sn !== $("span.dest_sn").text()) {
            var gate_status = $(this).data("status");
            $("span.dest_sn").text(gate_sn);
            $("span.gate_status").text(gate_status);
            $("span.gate_ready").text("");
            get_gatevserial_ready();
            Panelinst.close('#item-1');
        }

    });
}

/**
 *    set_api_result
 */
function set_api_result(data) {
    var local_datetime = new Date(parseInt(new Date().getTime())).toLocaleString('chinese', {hour12: false});
    $("span.apitime").text(local_datetime);
    $("pre.jsondataBox").text(JSON.stringify(data, null, 4));
}

/**
 *    set_notice_info
 */
function set_notice_info(data) {
    var local_datetime = new Date(parseInt(new Date().getTime())).toLocaleString('chinese', {hour12: false});
    $("span.Notietime").text(local_datetime);
    $("pre.NotiejsondataBox").text(JSON.stringify(data, null, 4));
}

/**
 *    get_gatevserial_ready
 */
function get_gatevserial_ready() {
    var gate_sn = $("span.dest_sn").text();
    if (gate_sn === '') {
        return false;
    }
    if (mqttc_connected) {
        console.log('查询网关vserial环境', gate_sn);
        var message = new Paho.Message(JSON.stringify({
            "id": 'vserial/ready/' + clientId + '/' + Date.parse(new Date()).toString(),
            "gate": gate_sn
        }));
        message.destinationName = 'v1/vserial/api/ready';
        message.qos = 0;
        mqtt_client.send(message);
    }


}


/**
 *    start_vserial
 */
function start_vserial() {
    if (in_start_action) {
        return false;
    }
    if (vserial_is_running) {
        mdui.snackbar({
            message: 'vserial已经启动！'
        });

    }
    if (gatevserial_ready && mqttc_connected) {
        console.log('启动vserial');
        var gate_sn = $("span.dest_sn").text();
        var nps_host = $("input[name='npsHost']").val();
        var nps_user = $("input[name='npsUser']").val();
        var auth_code = $("input[name='accesskey']").val();
        var gate_com = $("select.gate_com").val()
        if (isEmpty(gate_sn) || isEmpty(nps_host) || isEmpty(nps_user) || isEmpty(auth_code)) {
            mdui.snackbar({
                message: '请输入上面的必填信息！'
            });
            return false;
        }
        var start_data = {
            "id": 'vserial/start/' + clientId + '/' + Date.parse(new Date()).toString(),
            "host": nps_host,
            "user": nps_user,
            "gate": gate_sn,
            "gate_port": gate_com,
            "auth_code": auth_code
        };
        var message = new Paho.Message(JSON.stringify(start_data));
        message.destinationName = 'v1/vserial/api/start';
        message.qos = 0;
        mqtt_client.send(message);
        in_start_action = true;
        mdui.snackbar({
          message: '启动Vserial……'
        });
        setTimeout(function () {
            in_start_action = false;
        }, 5000);
    } else {
        mdui.snackbar({
            message: '未选择网关或网关不满足条件！'
        });
    }
}

/**
 *    stop_vserial
 */
function stop_vserial() {
    if (in_stop_action) {
        return false;
    }
    if (!vserial_is_running) {
        mdui.snackbar({
            message: 'vserial已经停止！'
        });
        return false;
    }
    if (mqttc_connected) {
        console.log('停止vserial');
        var stop_data = {
            "id": 'vserial/stop/' + clientId + '/' + Date.parse(new Date()).toString()
        };
        var message = new Paho.Message(JSON.stringify(stop_data));
        message.destinationName = 'v1/vserial/api/stop';
        message.qos = 0;
        mqtt_client.send(message);
        in_stop_action = true;
        mdui.snackbar({
          message: '停止Vserial……'
        });
        setTimeout(function () {
            in_stop_action = false;
        }, 5000);
    }
}

/**
 *    load_user_config
 */
function load_user_config() {
    if (vserial_is_running) {
        mdui.snackbar({
            message: 'vserial运行时不允许操作！'
        });
        return false;
    }
    if (mqttc_connected) {
        console.log('加载配置');
        var load_data = {
            "id": 'common/load/' + clientId + '/' + Date.parse(new Date()).toString()
        };
        var message = new Paho.Message(JSON.stringify(load_data));
        message.destinationName = 'v1/common/api/load';
        message.qos = 0;
        mqtt_client.send(message);
    } else {
        mdui.snackbar({
            message: '后台服务未连接！'
        });
    }
}

/**
 *    save_user_config
 */
function save_user_config() {
    if (vserial_is_running) {
        mdui.snackbar({
            message: 'vserial运行时不允许操作！'
        });
        return false;
    }
    if (mqttc_connected) {
        console.log('保存配置');
        var gate_sn = $("span.dest_sn").text();
        var nps_host = $("input[name='npsHost']").val();
        var nps_user = $("input[name='npsUser']").val();
        var auth_code = $.trim($("input[name='accesskey']").val());
        var save_data = {
            "id": 'common/save/' + clientId + '/' + Date.parse(new Date()).toString(),
            "npshost": nps_host,
            "npsuser": nps_user,
            "gate": gate_sn,
            "auth_code": auth_code
        };
        var message = new Paho.Message(JSON.stringify(save_data));
        message.destinationName = 'v1/common/api/save';
        message.qos = 0;
        mqtt_client.send(message);
    } else {
        mdui.snackbar({
            message: '后台服务未连接！'
        });
    }
}

/**
 *    remove_user_config
 */
function remove_user_config() {
    if (vserial_is_running) {
        mdui.snackbar({
            message: 'vserial运行时不允许操作！'
        });
        return false;
    }
    if (mqttc_connected) {
        mdui.snackbar({
          message: '移除本地保存的配置！'
        });
        var load_data = {
            "id": 'common/remove/' + clientId + '/' + Date.parse(new Date()).toString()
        };
        var message = new Paho.Message(JSON.stringify(load_data));
        message.destinationName = 'v1/common/api/remove';
        message.qos = 0;
        mqtt_client.send(message);
    } else {
        mdui.snackbar({
            message: '后台服务未连接！'
        });
    }
}