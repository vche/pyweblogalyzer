var getDashboardsDatatUrl = null;
var getDashBoardContextUrl = null;
var graphConfigs = null;
var getCalendarUrl = null;
var dashboardsGraphs = {};
var dtTimeformat = "";
var refreshTimer = null;

function initParameters(dashBoardDataUrl, dashBoardContextUrl, graphConfig, dtformat)
{
    getDashBoardContextUrl = dashBoardContextUrl;
    getDashboardsDatatUrl = dashBoardDataUrl;
    graphConfigs = graphConfig;
    dtTimeformat = dtformat;
}

function buildContextUrl(db_id, db_key) {
    return getDashBoardContextUrl.replace(
        '__DB_ID__', encodeURIComponent(db_id)).replace('__DB_KEY__', encodeURIComponent(db_key)
    );
}

function set_refresh(period_sec) {
    clearInterval(refreshTimer);
    $(".refresh_nav").each(function() {$(this).removeClass("active")});
    $("#refresh-" + period_sec).addClass("active");
    if (period_sec > 0) refreshTimer = setInterval(refreshDashboards, period_sec*1000);
}

function refreshDashboards() {
    $.get(getDashboardsDatatUrl, function(data) {dataReceived(data);});
}

function dataReceived(json_resp)
{
    $("#start_date").html(json_resp.start_date)
    $("#end_date").html(json_resp.end_date)
    for (i = 0; i < json_resp.dashboards.length; i++) {
        // Update badge if there is one
        if (json_resp.dashboards[i].hasOwnProperty('badge_id') &&
            json_resp.dashboards[i].hasOwnProperty('badge_value'))
        {
            $("#" + json_resp.dashboards[i].badge_id).html(json_resp.dashboards[i].badge_value);
        }

        // Update graph if there is one
        if (json_resp.dashboards[i].hasOwnProperty('graph_data')) {
            Plotly.restyle("db-card-chart-" + json_resp.dashboards[i].db_id, json_resp.dashboards[i].graph_data);
        }

        // Update tables
        dt = $("#db-card-table-" + json_resp.dashboards[i].db_id).DataTable();
        dt.clear(); // TODO: only send new elements, then don't clear
        dt.rows.add(json_resp.dashboards[i].table_data)
        dt.draw()
    }
    $("#last_update").html("Last updated: " + new Date(Date.now()).toLocaleTimeString())
    $('#loadsign').hide();
}

function modalDataReceived(modal_data) {
    if (modal_data) {
        $("#db_modal").html(modal_data.html);
        createDashboardTable(modal_data.table_id, ctxt = true, data=modal_data.table_data);
        $("#db_modal").modal('show');
    }
}

function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function formatFloatTime(ftime) {
    if (ftime < 1) return `${ftime * 1000} ms`;
    if (ftime < 60) return `${ftime.toFixed(3)} s`;
    time_str = ""
    rem = ftime
    if (ftime > 3600) {
        hours = Math.floor(ftime/3600)
        time_str += hours + " h ";
        rem = ftime - hours*3600;
    }
    mins = Math.floor(rem/60);
    secs = rem - mins*60;
    time_str += `${mins} min ${secs.toFixed(3)} s`;
    return time_str;
}

function createDashboardTable(tableId, ctxt = false, tab_data=null)
{
    col_renderer_classes = {
        'timestamp': 'datetime_column',
        'bytessent': 'size_column',
        'requesttime': 'time_column'
    }

    // Auto detect colums from the table header and add a class to customize rendering if needed
    var cols = [];
    var ctxt_key = 0;
    $('#' + tableId).find('thead tr th').each(function(index) {
        cols.push(this.innerText)
        col = this.innerText.replaceAll(" ","").replaceAll("\n","").toLowerCase();
        cls = col_renderer_classes[col]
        if (cls) $(this).addClass(cls);
        if ($(this).hasClass('key_column')) ctxt_key = index;
    });

    var dbTable = $('#'+tableId).DataTable( {
        // "columns": [{ "width": 25 },{  }],
        // "initComplete": function( settings, json ) {},
        data: tab_data,
        columnDefs: [
            {
                targets: "datetime_column",
                render: $.fn.dataTable.render.moment("YYYY-MM-DDTHH:mm:ssZZ", dtTimeformat),
            },
            {
                targets: "size_column",
                render: function ( data, type, row ) { return formatBytes(data) },
            },
            {
                targets: "time_column",
                render: function ( data, type, row ) { return formatFloatTime(data) },
            },
            {
                targets: "hidden_column",
                visible: false,
            },
            {
                targets: "order_column",
                order: 'desc',
            },
        ],
        "pageLength": 10,
        "responsive": true,
        "dom": datatable_dom(),
        "buttons": datatable_buttons(),
    } );

    // Add event listener when a row is clicked if not a contextual dashboard
    if (!ctxt) {
        $('#'+tableId).on('click', 'tbody tr', function() {
            db_id = tableId.split("db-card-table-")[1];
            db_key = dbTable.row(this).data()[ctxt_key];
            $.get(buildContextUrl(db_id, db_key), function(data) {modalDataReceived(data);});
        });
    }
  return dbTable
}

function createDashboardGraph(graphId)
{
    graph_chart = Plotly.newPlot(graphId,
      graphConfigs[graphId].data,
      graphConfigs[graphId].layout,
      graphConfigs[graphId].config,
    );
    return graph_chart;
}

function initDashboardTables() {
    // Create tables
    $('#dashboard-cards').find('.dashboard-card-table table').each(
        function() {
            createDashboardTable(this.id);
        }
    )
}

function initDashboardGraphs() {
    $('#dashboard-cards').find('.dashboard-card-graph div').each(
        function() {
            dashboardsGraphs[this.id] = createDashboardGraph(this.id);
        }
    )
}

function datatable_dom()
{
  // Style buttons top left, filter top right, rows/page bottom left, showed and pages bottom right
  return  "<'row db-hdr' <'custom-dt-btn col-sm-4 col-md-6'B> <'col-sm-6 col-md-6'f>  >" +
          "<'row' <'col-sm-12 'tr> >" +
          "<'row db-hdr' <'col-sm-12 col-md-4'l> <'col-sm-12 col-md-4'i><'col-sm-12 col-md-4'p>>"
}

function datatable_buttons()
{
  // Define col button menu with col selection, and export button menu with exports
  return [
    {
      extend: 'colvis',
      collectionLayout: 'two-column',
      text: "Hide columns",
      className: "db-hdr-dropdown",
      prefixButtons: [
        {
          extend: 'colvisGroup',
          text: 'Show all',
          show: ':hidden'
        },
        {
          extend: 'colvisRestore',
          text: 'Restore'
        }
      ]
    },
    {
      extend: 'collection',
      text: 'Export',
      buttons: [
        {
          text: 'Copy',
          extend: 'copyHtml5',
          footer: false,
          exportOptions: { columns: ':visible' }
        },
        {
          text: 'CSV',
          extend: 'csvHtml5',
          fieldSeparator: ';',
          exportOptions: { columns: ':visible' }
        },
        {
          text: 'Print',
          extend: 'print',
          fieldSeparator: ';',
          exportOptions: { columns: ':visible' }
        },
     ]
    }
  ]
}


// Page start, to execute when the page is fully loaded
function pageStart()
{
    // Show the loader, hide the dashboards; and request the data
    $('#loadsign').show();

    // Create the datatables of each dashboard
    initDashboardTables();
    initDashboardGraphs();

    // Request dashboards data
    refreshDashboards();
}
