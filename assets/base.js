$(function(){
    // prevent overflow
    $(".fix-height").each(function(){
        let $this = $(this);
        $this.css("max-height", $this.height());
        new SimpleBar(this);
    });

    $("#close").click(function(){
        pywebview.api.close();
    });

    $("#minimize").click(function(){
        pywebview.api.minimize();
    });

    $("#nav-items img").not(".control").click(function(){
        const page_id = $(this).attr('data-for');
        showPopPage(page_id);
    });

    $(".pop-close").click(function(){
        $("#pop-mask").fadeOut(300);
        $(this).parents(".pop-page").fadeOut(300);
    });

    $(".frame-head>span").click(function(){
        let $this = $(this);
        if($this.hasClass("frame-head-active")){
            return;
        }
        $this.siblings().removeClass("frame-head-active");
        $this.addClass("frame-head-active");

        let $body = $("#"+$this.attr("data-for"));
        $body.siblings().hide();
        $body.show();
    });
    // set first page at starting
    $(".frame-head>span:last-child").click();

    $(".tree-root").on("click", ".directory, .file-folder", function(e){
        $(this).children("ul").slideToggle(300);
        $(this).children("img").toggleClass("arrow-expanded");
        e.stopPropagation();
    });
    $(".tree-root").on("click", ".file", function(e){
        const $this = $(this);
        // avoid reloading file
        if ($this.attr("data-loaded")){
            $(this).children("ul").slideToggle(300);
            $(this).children("img").toggleClass("arrow-expanded");
            e.stopPropagation();
            return;
        }
        
        /* Load file data */
        // get file path
        let paths = new Array();
        for (let $li = $this;;){
            paths.push($li.attr("data-name"));
            
            let $upper_li = $li.parent("ul").parent("li");
            if (!$upper_li.length){
                break;
            }
            $li = $upper_li;
        }
        paths = paths.reverse()
        console.log(paths);

        // require tree and update DOM 
        const tree = pywebview.api.load_folder_file(paths).then(function(tree){
            console.log(tree);

            let $tree = $("<ul>").appendTo($this);
            setFileTree($tree, tree);
            $('<img src="svg/arrow.svg" class="arrow-expanded"/>'
                ).prependTo($this);
            $this.attr("data-loaded", true);
        });
        e.stopPropagation();
    });
    $(".tree-root").on("click", ".file-entry", function(e){
        const code = $(this).children(".std-code").text();
        const title = $(this).children(".std-title").text();
        setStandard(code, title);
        e.stopPropagation();
    });

    $("#search-button").click(function(){
        const query = $("#search-input").val();
        const $results = $("#search-results");

        // clear old results
        $results.empty();
        
        pywebview.api.is_concret_code(query).then(function(concret) {
            if (concret) {
                setStandard(query, '');
                return
            } 
            pywebview.api.search_standards(query).then(function(standards) {
                if (standards == 'TOO_MANY_RESULTS') {
                    $results.append($("<p>结果过多，请更换搜索词</p>"));
                    return
                } else if (standards.length === 0) {
                    $results.append($("<p>无搜索结果</p>"));
                    return
                }
                $.each(standards, function(i, standard) {
                    $("<li class='search-result'>")
                        .append($("<div class='search-head'>")
                            .append($("<div class='search-code'>").text(standard.code))
                            .append($("<div class='search-status'>").text(standard.status))
                            )
                        .append($("<div class='search-title'>").text(standard.title))
                        .click(function() { setStandard(standard.code) })
                        .appendTo($results);
                });
            });
        });
    });

    $("#standard-download").click(function(){
        let code = $("#standard-main").attr("data-code");
        const $icons = $("#standard-download-icon img");

        $icons.hide();
        $icons.filter("#standard-downloading").show();

        pywebview.api.download_standard(code).then(function(status){
            $icons.filter("#standard-downloading").hide();
            if (status==true){
                $icons.filter("#standard-downloaded").show();
                showPopMessage('', code+' 下载成功');
                load_local_tree();
            } else if (status=='EXISTS'){
                $icons.filter("#standard-downloaded").show();
                showPopMessage('', code+' 已存在');
            } else if (status=='NOT_FOUND'){
                $icons.filter("#standard-download").show();
                showPopMessage('', code+'无法找到下载源');
            } 
        });
    });
    $("#standard-downloaded").click(function(){
        let code = $("#standard-main").attr("data-code");
        pywebview.api.open_standard_pdf(code).then(function(success){
            if (!success){
                showPopMessage('', '找不到文件');
                load_local_tree();
            }
        });
    });

    $("#standard-substitute").click(function(){
        setStandard($(this).text(), '');
    });
});


function setStandard(code, title) {
    const $main = $("#standard-main");
    if (code==$main.attr('data-code')){
        $main.show();
        return;
    }

    $main.attr('data-code', code);
    let fields = [
        'title_english', 'issued_by', 'issuance_date',
        'implementation_date', 'status'
        ];
    if (!title){
        fields.unshift('title');
    }
    
    $("#loading-mask").fadeIn(100);
    pywebview.api.get_fields(code, fields).then(function(results){
        console.log(results);
        $("#loading-mask").fadeOut(200);
        $main.show();

        $main.find('span[id*="standard-"]').text('');
        if (title) {
            $main.find("#standard-title").text(title);
        }
        $main.find('#standard-code').text(code);
        for (const field in results){
            $("#standard-"+field).text(results[field]);
        }
        if (results['status'] == '过时') {
            pywebview.api.get_fields(code, ['substitute']
            ).then(function(results){
                $("#standard-substitute").text(results['substitute']).parent().show();
            });
        } else {
            $("#standard-substitute").parent().hide();
        }

        $("#standard-download-icon>img").hide();
        if ($("#downloaded-root").find(".std-code:contains("+code+")").length) {
            $("#standard-downloaded").show();
        } else {
            $("#standard-download").show();
        }
    });
}

function showPopPage(id) {
    const $base = $("#base-container");
    $base.find(".pop-page").hide();
    $base.find("#pop-mask").fadeIn(300);
    const $popPage = $base.find("#"+id);
    $popPage.fadeIn(300);
    return $popPage;
}

function showPopMessage(title, message, ...buttons) {
    if (!buttons.length){
        buttons.push({
            'text': '确定',
            'func': function(){
                $("#pop-message").fadeOut(300);
                $("#pop-mask").fadeOut(300);
            }
        });
    }

    const $pop = $("#pop-message");
    const $buttons = $pop.children("#message-buttons");
    const $content = $pop.children("#message-text");

    $pop.children("#message-title").text(title);
    $content.children().remove();
    if (typeof message === 'string') {
        $('<p class="content-block"></p>')
            .text(message)
            .appendTo($content);
    } else {
        message.appendTo($content);
    }

    $buttons.children().remove();
    for (const button of buttons) {
        $('<div class="button"></div>')
            .text(button.text)
            .click(button.func)
            .appendTo($buttons);
    }

    $("#pop-mask").fadeIn(300);
    $pop.fadeIn(300);
}

function showBZOrgLoginMessage(url){
    const $message = $(`
<div class="content-block">
    <img src="${url}" alt="login-pr-code" height="100px" width="100px"/>
    <p>
        下载源“标准网”需要您使用微信扫码以登录其账户。扫码确认登录后请耐心等待下载完成。
    </p>
</div>
<div class="content-block">
    <p>
        该下载源仅对注册用户提供标准下载，
        在每日下载限额(5份)内不需付费。
        如果您当前不愿意登录到该站，请点击“取消”。
    </p>
    <p>
        如若不希望再收到该站的登录请求，
        请在“设置”中停用该源。
        注意，停用很可能会导致下载来源不足。
    </p>
</div>`);
    const button = {
        'text': '取消',
        'func': function(){
            $("#pop-message").fadeOut(300);
            $("#pop-mask").fadeOut(300);
            pywebview.api.cancel_login('bzorg').then();
        }
    }
    showPopMessage('登录', $message, button);
}

function setTree(node, tree, nodeClass, endNodeClass) {
    node.children().remove();
    for (const subnode of tree){
        let $subnode;
        if (!Array.isArray(subnode)){
            $subnode = $(
                '<li class="'+endNodeClass+'"></li>'
                );
            if (endNodeClass=='file'){
                $subnode.attr('data-name', subnode);
                text = subnode.split(".", 1)[0];
                $("<span>").text(text).appendTo($subnode);
            } else if (endNodeClass=='file-entry'){
                $('<p class="std-title">').text(subnode.title).appendTo($subnode);
                $('<p class="std-code">').text(subnode.code).prependTo($subnode);
            }
        } else {
            let name = subnode[0];
            if (name.indexOf("_") != -1) {
                name = name.split("_").pop();
            }
            $subnode = $('<li class="'+nodeClass+'" data-name="'+subnode[0]+'">' +
                '<img src="svg/arrow.svg"/>' +
                "<span>"+name+"</span>" +
                "<ul></ul>" +
                "</li>");
            setTree(
                $subnode.children("ul"),
                subnode[1],
                nodeClass,
                endNodeClass
                );
        }
        $subnode.children("ul").slideUp(0);
        $subnode.appendTo(node);
    }
}
function setDirectoryTree(node, tree){
    setTree(node, tree, 'directory', 'file');
}
function setFileTree(node, tree){
    setTree(node, tree, 'file-folder', 'file-entry');
}

function load_local_tree(){
    pywebview.api.load_local().then(function(tree){
        console.log(tree);
        setFileTree($("#downloaded-root"), tree);
    });
}

window.addEventListener("pywebviewready", function(){
    pywebview.api.load_folder().then(function(tree){
        setDirectoryTree($("#folder-root"), tree);
    });
    load_local_tree();
});