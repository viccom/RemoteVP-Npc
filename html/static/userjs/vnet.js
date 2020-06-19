var vnetStatusOBJ = new Object();
var gatevnet_ready = false;
var vnet_is_running = false;
var in_start_action = false;
var in_stop_action = false;

//--------------------------周期检测和后台MQTT服务是否连接--------------------------------------
var mqtt_status_ret= setInterval(function(){
      if (mqttc_connected) {
          $('button.mqtt-connect-btn').html('<i class="mdui-icon material-icons mdui-color-green">highlight</i>')
      } else {
          $('button.mqtt-connect-btn').html('<i class="mdui-icon material-icons">highlight</i>');
          $('span.start_vnet').addClass('mdui-color-grey');
          $('span.start_vnet').removeClass('mdui-color-green');
      }
    },1000);

//--------------------------Vnet运行时每20秒发送保持心跳--------------------------------------
var keep_alive_ret= setInterval(function(){
    if (mqttc_connected && vnet_is_running) {
        var message = new Paho.Message(JSON.stringify({"id":'vnet/ping/' + clientId + '/' + Date.parse(new Date()).toString()   }));
        message.destinationName = 'v1/vnet/api/ping';
        message.qos = 0;
        mqtt_client.send(message);
    }
    },20000);

//--------------------------周期通过状态信息更改页面状态--------------------------------------
var vnet_ret= setInterval(function(){
    if(!$.isEmptyObject(vnetStatusOBJ)){
        if(vnet_is_running){
            var gate_sn = $("span.dest_sn").text();
           if(isEmpty(gate_sn)){
                $("span.dest_sn").text(vnetStatusOBJ.userinfo.gate);
                get_gatevnet_ready();
                $("input[name='npsHost']").val(vnetStatusOBJ.userinfo.tunnel_host);
                $("input[name='npsUser']").val(vnetStatusOBJ.userinfo.name);
           }
           var dest_ip = $("input[name='destIP']").val();
           if(isEmpty(dest_ip)){
               $("input[name='destIP']").val(vnetStatusOBJ.userinfo.dest_ip);
           }
            $("span.localvnetstatus").text(vnet_is_running);
            $("span.gatevnetstatus").text(vnetStatusOBJ.gate_vpn_is_running);
            $("span.cloudclientstatus").text(vnetStatusOBJ.userinfo.client_online);
            $("span.localvnetip").text(vnetStatusOBJ.userinfo.local_vnet_ip);
            $("span.gatelanip").text(vnetStatusOBJ.userinfo.gate_lan_ip);
            if(!$.isEmptyObject(vnetStatusOBJ.ip_alive)){
                $("span.pingdestip").text(vnetStatusOBJ.ip_alive.delay);
            }
        }else{
            $("span.localvnetstatus").text(vnet_is_running);
            $("span.gatevnetstatus").text("UNKNOWN");
            $("span.cloudclientstatus").text("UNKNOWN");
            $("span.localvnetip").text("UNKNOWN");
            $("span.gatelanip").text("UNKNOWN");
            $("span.pingdestip").text("UNKNOWN");
        }
    }else{
        $("span.localvnetstatus").text("UNKNOWN");
        $("span.gatevnetstatus").text("UNKNOWN");
        $("span.cloudclientstatus").text("UNKNOWN");
        $("span.localvnetip").text("UNKNOWN");
        $("span.gatelanip").text("UNKNOWN");
        $("span.pingdestip").text("UNKNOWN");
    }

    },2000);

/**
 *	get_user_gatelist
 */
function get_user_gatelist() {
    var user_accesskey = $.trim($("input[name='accesskey']").val());
    console.log(user_accesskey);
    if(isEmpty(user_accesskey)) {
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
    if(mqttc_connected){
        console.log('查询当前用户gatelist');
        var message = new Paho.Message(JSON.stringify({"id":'common/gatelist/' + clientId + '/' + Date.parse(new Date()).toString(),"auth_code": user_accesskey   }));
        message.destinationName = 'v1/common/api/gatelist';
        message.qos = 0;
        mqtt_client.send(message);
    }
}

/**
 *	creat_gatelist_table
 */
function creat_gatelist_table(obj, tableobj) {
    var trhtml = '';
    $.each(obj, function (i, val) {
        trhtml = trhtml + '<tr data-id="' + val.device_sn + '" data-status="' + val.device_status + '">' +
            '<td>' + val.device_name + '</td>' +
            '<td>' + val.device_sn + '</td>' +
            '<td>' +  val.device_status +  '</td>' +
            '</tr>'

    })
    tableobj.empty();
    tableobj.append(trhtml);

    tableobj.on('click', 'tr', function () {
        if (vnet_is_running) {
            return false;
        }
        var gate_sn = $(this).data("id");
        $(this).addClass("mdui-table-row-selected");
        if (gate_sn !== $("span.dest_sn").text()) {
            var gate_status = $(this).data("status");
            $("span.dest_sn").text(gate_sn);
            $("span.gate_status").text(gate_status);
            $("span.gate_ready").text("");
            get_gatevnet_ready();
            Panelinst.close('#item-1');
        }

    });
}

/**
 *	set_api_result
 */
function set_api_result(data) {
    var local_datetime = new Date(parseInt(new Date().getTime())).toLocaleString('chinese', { hour12: false });
    $("span.apitime").text(local_datetime);
    $("pre.jsondataBox").text(JSON.stringify(data, null, 4));
}

/**
 *	set_notice_info
 */
function set_notice_info(data) {
    var local_datetime = new Date(parseInt(new Date().getTime())).toLocaleString('chinese', { hour12: false });
    $("span.Notietime").text(local_datetime);
    $("pre.NotiejsondataBox").text(JSON.stringify(data, null, 4));
}

/**
 *	get_gatevnet_ready
 */
function get_gatevnet_ready() {
    var gate_sn = $("span.dest_sn").text();
        if(gate_sn==='') {
            return false;
        }
    if (mqttc_connected) {
        console.log('查询网关Vnet环境', gate_sn);
        var message = new Paho.Message(JSON.stringify({
            "id": 'vnet/ready/' + clientId + '/' + Date.parse(new Date()).toString(),
            "gate": gate_sn
        }));
        message.destinationName = 'v1/vnet/api/ready';
        message.qos = 0;
        mqtt_client.send(message);
    }


}


/**
 *	start_vnet
 */
function start_vnet() {
    if(in_start_action){
        return false;
    }
    if(vnet_is_running){
        mdui.snackbar({
          message: 'Vnet已经启动！'
        });

    }
    if(gatevnet_ready  && mqttc_connected){
        console.log('启动Vnet');
        var gate_sn = $("span.dest_sn").text();
        var nps_host = $("input[name='npsHost']").val();
        var nps_user = $("input[name='npsUser']").val();
        var auth_code = $("input[name='accesskey']").val();
        var dest_ip = $("input[name='destIP']").val();
        if(isEmpty(gate_sn) || isEmpty(nps_host) || isEmpty(nps_user) || isEmpty(auth_code)){
            mdui.snackbar({
              message: '请输入上面的必填信息！'
            });
            return false;
        }
        var start_data = {
            "id": 'vnet/start/' + clientId + '/' + Date.parse(new Date()).toString(),
            "host": nps_host,
            "user": nps_user,
            "gate": gate_sn,
            "dest_ip": dest_ip,
            "auth_code": auth_code
        };
        var message = new Paho.Message(JSON.stringify(start_data));
        message.destinationName = 'v1/vnet/api/start';
        message.qos = 0;
        mqtt_client.send(message);
        in_start_action =  true;
        mdui.snackbar({
          message: '启动Vnet……'
        });
        setTimeout(function () {
            in_start_action =  false;
        }, 5000);
    }else{
        mdui.snackbar({
          message: '未选择网关或网关不满足条件！'
        });
    }
}

/**
 *	stop_vnet
 */
function stop_vnet() {
    if(in_stop_action){
        return false;
    }
    if(!vnet_is_running){
        mdui.snackbar({
          message: 'Vnet已经停止！'
        });
        return false;
    }
    if(mqttc_connected){
        console.log('停止Vnet');
        var stop_data = {
            "id": 'vnet/stop/' + clientId + '/' + Date.parse(new Date()).toString()
        };
        var message = new Paho.Message(JSON.stringify(stop_data));
        message.destinationName = 'v1/vnet/api/stop';
        message.qos = 0;
        mqtt_client.send(message);
        in_stop_action = true;
        mdui.snackbar({
          message: '停止Vnet……'
        });
        setTimeout(function () {
            in_stop_action =  false;
        }, 5000);
    }
}

/**
 *	load_user_config
 */
function load_user_config() {
    if(vnet_is_running){
        mdui.snackbar({
          message: 'Vnet运行时不允许操作！'
        });
        return false;
    }
    if(mqttc_connected){
        console.log('加载配置');
        var load_data = {
            "id": 'common/load/' + clientId + '/' + Date.parse(new Date()).toString()
        };
        var message = new Paho.Message(JSON.stringify(load_data));
        message.destinationName = 'v1/common/api/load';
        message.qos = 0;
        mqtt_client.send(message);
    }else{
        mdui.snackbar({
          message: '后台服务未连接！'
        });
    }
}

/**
 *	save_user_config
 */
function save_user_config() {
    if(vnet_is_running){
        mdui.snackbar({
          message: 'Vnet运行时不允许操作！'
        });
        return false;
    }
    if(mqttc_connected){
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
    }else{
        mdui.snackbar({
          message: '后台服务未连接！'
        });
    }
}

/**
 *	remove_user_config
 */
function remove_user_config() {
    if(vnet_is_running){
        mdui.snackbar({
          message: 'Vnet运行时不允许操作！'
        });
        return false;
    }
    if(mqttc_connected){
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
    }else{
        mdui.snackbar({
          message: '后台服务未连接！'
        });
    }
}