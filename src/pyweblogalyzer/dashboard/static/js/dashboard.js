var getDashboardsDatatUrl = null;
var getDashBoardContextUrl = null;
var graphConfigs = null;
var getCalendarUrl = null;
var dashboardsGraphs = {};
var dtTimeformat = "";

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

    $('#loadsign').hide();
}

function modalDataReceived(modal_data) {
    if (modal_data) {
        $("#db_modal").html(modal_data.html);
        createDashboardTable(modal_data.table_id, ctxt = true, data=modal_data.table_data);
        $("#db_modal").modal('show');
    }
}

function createDashboardTable(tableId, ctxt = false, tab_data=null)
{
    // Detect colums from the table header
    var cols = [];
    $('#' + tableId).find('thead tr th').each(function() {
        cols.push(this.innerText)});

    var dbTable = $('#'+tableId).DataTable( {
        // "columns": [{ "width": 25 },{  }],
        // "initComplete": function( settings, json ) {},
        data: tab_data,
        columnDefs: [ {
            targets: "time_column",
            render: $.fn.dataTable.render.moment("YYYY-MM-DDTHH:mm:ssZZ", dtTimeformat)
        } ],
        "pageLength": 10,
        "responsive": true,
        "dom": datatable_dom(),
        "buttons": datatable_buttons(),
        "order": [[cols.length-1, 'desc']]
    } );

    if (!ctxt) {
        $('#'+tableId).on('click', 'tbody tr', function() {
            db_id = tableId.split("db-card-table-")[1];
            db_key = dbTable.row(this).data()[0];
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
    $.get(getDashboardsDatatUrl, function(data) {dataReceived(data);});
}
