odoo.define('web.stock_query', function(require) {
    var Client = require('web.WebClient');
    var Model = require('web.DataModel');
    var Core = require('web.core');

    Client.include({
        show_application: function() {
            this._super.apply(this, arguments);
            this.show_stock_query();
            this.$board = false;
            if(window.localStorage.getItem("a") === '10') {
              $('body').removeClass('style1').removeClass('style2').addClass('style0');
            } else if (window.localStorage.getItem("b") === '10') {
                $('body').removeClass('style0').removeClass('style2').addClass('style1');
            } else if (window.localStorage.getItem("c") === '10') {
                $('body').removeClass('style0').removeClass('style1').addClass('style2');
            }

        },

        show_stock_query: function() {
            var self = this,
            // 页面风格按钮

                $query = $('<ul class="nav navbar-nav navbar-right nav-stock-query"><li><a class="dropdown-toggle" data-toggle="dropdown" aria-expanded="false"><span>页面风格</span><b class="caret"></b></a><ul class="dropdown-menu o_debug_dropdown" role="menu"><li class="color"><a class="toggle_technical_features1" href="#">亮海蓝<span id="blue1"></span></a></li><li class="color"><a class="toggle_technical_features2" href="#">深天蓝<span id="black1"></span></a></li><li class="color"><a class="toggle_technical_features3" href="#">亮珊瑚<span id="white1"></span></a></li></ul></li></ul>');
                // $query = $('<ul class="nav navbar-nav navbar-right nav-stock-query"><li><input type="text" placeholder="库存查询"/><a class="query"></a><a class="destroy"></a><div class="stock-query-search-list"/></li></ul>'),
            $li = $query.find('.color'),
            $input = $query.find('span'),
            $destroy = $query.find('.destroy');
            // 获得页头li标签
            $lis=$('.oe_application_menu_placeholder').children();
           // 删除页头li标签中的open属性
            $lis.on('click','a',function(e) {
                e.preventDefault();
                $lis.removeClass('open');

            })
            // 删除页头li标签鼠标悬停时的open属性
            $lis.hover(function(e) {
                e.preventDefault();
                $lis.removeClass('open');

            })
            // 删除页头li标签鼠标悬停时的open属性
            $('.o_user_menu').hover(
                function(e) {
                    e.preventDefault();
                    $('.o_user_menu').removeClass('open');

                }
            );
            // 给页面风格下拉框绑定点击事件
            $li.on('click','a',function(e) {
                e.preventDefault();
                $a = $(e.currentTarget);
                if ($a.is('.toggle_technical_features1')) {
                    $('body').removeClass('style1').removeClass('style2').addClass('style0');
                    $('[class=oe_application_menu_placeholder]').find('[class=open]').removeClass('open');
                    window.localStorage.setItem("a",10);
                    window.localStorage.removeItem("b");
                    window.localStorage.removeItem("c");
                } else if ($a.is('.toggle_technical_features2')) {
                    $('body').removeClass('style0').removeClass('style2').addClass('style1');
                    $('[class=oe_application_menu_placeholder]').find('[class=open]').removeClass('open');
                    window.localStorage.setItem("b",10)
                     window.localStorage.removeItem("a");
                    window.localStorage.removeItem("c");
                } else if ($a.is('.toggle_technical_features3')) {
                    $('body').removeClass('style1','style0').addClass('style2');
                    $('[class=oe_application_menu_placeholder]').find('[class=open]').removeClass('open');
                    window.localStorage.setItem("c",10);
                    window.localStorage.removeItem("b");
                    window.localStorage.removeItem("a");
                }
            })

            // 将页面风格加入页头
            $('.oe_systray').before($query);
        },

    });
});
