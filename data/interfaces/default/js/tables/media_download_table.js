var date_format = 'YYYY-MM-DD';
var time_format = 'hh:mm a';

$.ajax({
    url: 'get_date_formats',
    type: 'GET',
    success: function (data) {
        date_format = data.date_format;
        time_format = data.time_format;
    }
});


media_download_table_options = {
    "destroy": true,
    "language": {
        "search": "Search: ",
        "lengthMenu": "Show _MENU_ entries per page",
        "info": "Showing _START_ to _END_ of _TOTAL_ library items",
        "infoEmpty": "Showing 0 to 0 of 0 entries",
        "infoFiltered": "<span class='hidden-md hidden-sm hidden-xs'>(filtered from _MAX_ total entries)</span>",
        "emptyTable": "No data in table",
        "loadingRecords": '<i class="fa fa-refresh fa-spin"></i> Loading items...</div>'
    },
    "paging": false,
    "stateSave": true,
    "processing": false,
    "serverSide": true,
    "order": [0, 'asc'],
    "autoWidth": false,
    "scrollX": true,
    "scrollY": "90%",
    "columnDefs": [
        {
            "targets": [0],
            "data": "title",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (rowData) {
                    var expand_details = '';
                    var media_count = 0;
                    var media_type = '';
		    var title = cellData;
                    if (rowData['media_type']) { media_type = rowData['media_type']; }
		    if (rowData['year']) { title = title + " (" + rowData['year'] + ")"; }
		    if (rowData['ratingKey']) {
			var id = rowData['ratingKey'];
			if (id.match(/tt(\d+)/)) {
			    title = '<a target="_blank" href="http://www.imdb.com/title/' + id + '">' + title + '</a>';
			} else {
			    title = '<a target="_blank" href="https://www.themoviedb.org/movie/' + id + '">' + title + '</a>';
			}
		    }
                    if (media_type === 'movie') {
                        content = '<span class="media-type-tooltip" data-toggle="tooltip" title="Movie"><i class="fa fa-film fa-fw"></i></span>';
                        if (media_count > 1) {
                            content = content + '<span class="expand-media-download-tooltip" data-toggle="tooltip" title="Show Parts"><i class="fa fa-plus-circle fa-fw"></i></span>';
                        }
                        content = content + " " + title;
                        $(td).html('<div><a href="#"><div style="float: left;">' + content + '</div></a></div>');
                    } else if (media_type === 'show') {
                        content = '<span class="media-type-tooltip" data-toggle="tooltip" title="TV Show"><i class="fa fa-television fa-fw"></i></span>' + 
                                  '<span class="expand-media-download-tooltip" data-toggle="tooltip" title="Show Seasons"><i class="fa fa-plus-circle fa-fw"></i></span>' +
                                  cellData;
                        $(td).html('<div><a href="#"><div style="float: left;">' + content + '</div></a></div>');
                    } else if (media_type === 'season') {
                        content = '<span class="media-type-tooltip" data-toggle="tooltip" title="Season"><i class="fa fa-television fa-fw"></i></span>' +
                                  '<span class="expand-media-download-tooltip" data-toggle="tooltip" title="Show Episodes"><i class="fa fa-plus-circle fa-fw"></i></span>' +
                                  cellData;
                        $(td).html('<div><a href="#"><div style="float: left;">' + content + '</div></a></div>');
		    } else if (media_type === 'episode') {
                        content = '<span class="media-type-tooltip" data-toggle="tooltip" title="Episode"><i class="fa fa-television fa-fw"></i></span>' + 
                                  cellData;
                        $(td).html('<div><a href="#"><div style="float: left;">' + content + '</div></a></div>');
                    } else if (media_type === 'artist') {
                        content = '<span class="media-type-tooltip" data-toggle="tooltip" title="Artist"><i class="fa fa-music fa-fw"></i></span>' +
                                  '<span class="expand-media-download-tooltip" data-toggle="tooltip" title="Show Albums"><i class="fa fa-plus-circle fa-fw"></i></span>' +
                                  cellData;
                        $(td).html('<div><a href="#"><div style="float: left;">' + content + '</div></a></div>');
                    } else if (media_type === 'album') {
                        content = '<span class="media-type-tooltip" data-toggle="tooltip" title="Album"><i class="fa fa-music fa-fw"></i></span>' +
                                  '<span class="expand-media-download-tooltip" data-toggle="tooltip" title="Show Tracks"><i class="fa fa-plus-circle fa-fw"></i></span>' + 
                                  cellData;
                        $(td).html('<div><a href="#"><div style="float: left;">' + content + '</div></a></div>');
                    } else if (media_type === 'track') {
                        content = '<span class="media-type-tooltip" data-toggle="tooltip" title="Track"><i class="fa fa-music fa-fw"></i></span>' + 
                                  cellData;
                        $(td).html('<div><a href="#"><div style="float: left;">' + content + '</div></a></div>');
                    } else {
                        $(td).html('<div style="float: left;"><i class="fa fa-fw"></i>&nbsp;</div>');
                    }
                }
            },
            "width": "40%",
            "className": "no-wrap expand-media-download",
            "searchable": false
        },
        {
            "targets": [1],
            "data": "confidence",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
		    confidence = cellData * 100.0;
                    $(td).html(confidence + "%");
                }
            },
            "width": "10%",
            "className": "no-wrap"
        },
        {
            "targets": [2],
            "data": "activity",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    var parent_info = '';
                    var media_type = '';
		    var btn_del = '';
		    var btn_edit = '';
		    var btn_transcode = '';

		    if (cellData['delete']) {
                        btn_del = '<button class="btn btn-danger btn-dark" data-toggle="button" id="delete-media"><i class="fa fa-trash-o"></i></button>&nbsp;';
		    }
		    if (cellData['edit']) {
                        btn_edit = '<button class="btn btn-dark" data-toggle="button" id="edit-media"><i class="fa fa-edit"></i></button>&nbsp;';
		    }
                    $(td).html('<div class="btn-group">' + btn_del + btn_edit + '&nbsp;</div>');
                }
            },
            "width": "20%",
            "className": "no-wrap",
        },
    ],
    "drawCallback": function (settings) {
        // Jump to top of page
        // $('html,body').scrollTop(0);
        $('#ajaxMsg').fadeOut();

        // Create the tooltips.
        $('.expand-media-download-tooltip').tooltip({ container: 'body' });
        $('.media-type-tooltip').tooltip({ container: 'body' });

        media_download_table.rows().every(function () {
            var rowData = this.data();
            if (rowData['rating_key'] in media_download_child_table) {
                // if a child table was already created
                $(this.node()).find('i.fa.fa-plus-circle').toggleClass('fa-plus-circle').toggleClass('fa-minus-circle');
                this.child(childTableFormatMediaDownload(rowData)).show();
                createChildTableMediaDownload(this, rowData)
            }
        });

        /*$("#media_download_table-ST-" + section_type + "_info").append('<span class="hidden-md hidden-sm hidden-xs"> with a total file size of ' +
            humanFileSize(settings.json.filtered_file_size) +
            ' (filtered from ' + humanFileSize(settings.json.total_file_size) + ')</span>');
	*/
    },
    "preDrawCallback": function (settings) {
        var msg = "<i class='fa fa-refresh fa-spin'></i>&nbspFetching rows...";
        showMsg(msg, false, false, 0)
    },
    "rowCallback": function (row, rowData, rowIndex) {
        if (rowData['rating_key'] in media_download_child_table) {
            // if a child table was already created
            $(row).addClass('shown')
            media_download_table.row(row).child(childTableFormatMediaDownload(rowData)).show();
        }
    }
}

// Parent table expand detailed media info
$('.media_download_table').on('click', '> tbody > tr > td.expand-media-download a', function () {
    var tr = $(this).closest('tr');
    var row = media_download_table.row(tr);
    var rowData = row.data();

    $(this).find('i.fa').toggleClass('fa-plus-circle').toggleClass('fa-minus-circle');

    if (row.child.isShown()) {
        $('div.slider', row.child()).slideUp(function () {
            row.child.hide();
            tr.removeClass('shown');
            delete media_download_child_table[rowData['rating_key']];
        });
    } else {
        tr.addClass('shown');
        row.child(childTableFormatMediaDownload(rowData)).show();
        createChildTableMediaDownload(row, rowData);
    }
});

// Initialize the detailed media info child table options using the parent table options
function childTableOptionsMediaDownload(rowData) {
    switch (rowData['media_type']) {
        case 'show':
            section_type = 'season';
            break;
        case 'season':
            section_type = 'episode';
            break;
        case 'artist':
            section_type = 'album';
            break;
        case 'album':
            section_type = 'track';
            break;
    }

    opts = media_download_table_options;
    // Remove settings that are not necessary
    opts.searching = false;
    opts.lengthChange = false;
    opts.info = false;
    opts.pageLength = 10;
    opts.bStateSave = false;
    opts.ajax = {
        url: 'get_library_media_downloads',
        type: 'post',
        data: function (d) {
            return {
                json_data: JSON.stringify(d),
                section_type: section_type,
                rating_key: rowData['rating_key']
            };
        }
    }
    opts.fnDrawCallback = function (settings) {
        $('#ajaxMsg').fadeOut();

        // Create the tooltips.
        $('.expand-media-download-tooltip').tooltip({ container: 'body' });
        $('.media-type-tooltip').tooltip();

        if (rowData['rating_key'] in media_download_child_table) {
            media_download_child_table[rowData['rating_key']].rows().every(function () {
                var childrowData = this.data();
                if (childrowData['rating_key'] in media_download_child_table) {
                    // if a child table was already created
                    $(this.node()).find('i.fa.fa-plus-circle').toggleClass('fa-plus-circle').toggleClass('fa-minus-circle');
                    this.child(childTableFormatMediaDownload(childrowData)).show();
                    createChildTableMediaDownload(this, childrowData)
                }
            });
        }

        $(this).closest('div.slider').slideDown();
    }
    opts.fnRowCallback = function (row, rowData, rowIndex) {
        if (rowData['rating_key'] in media_download_child_table) {
            // if a child table was already created
            $(row).addClass('shown')
            media_download_table.row(row).child(childTableFormatMediaDownload(rowData)).show();
        }
    }

    return opts;
}

// Format the detailed media info child table
function childTableFormatMediaDownload(rowData) {
    return '<div class="slider">' +
            '<table id="media_download_child-' + rowData['rating_key'] + '" data-id="' + rowData['rating_key'] + '" width="100%">' +
            '<thead>' +
            '<tr>' +
                '<th align="left" id="title">Title</th>' +
                '<th align="center" id="confidence">Confidence</th>' + 
                '<th align="left" id="activity">Activity</th>' +
            '</tr>' +
            '</thead>' +
            '<tbody>' +
            '</tbody>' +
            '</table>' +
            '</div>';
}

// Create the detailed media info child table
media_download_child_table = {};
function createChildTableMediaDownload(row, rowData) {
    media_download_table_options = childTableOptionsMediaDownload(rowData);
    // initialize the child table
    media_download_child_table[rowData['rating_key']] = $('#media_download_child-' + rowData['rating_key']).DataTable(media_download_table_options);

    // Set child table column visibility to match parent table
    var visibility = media_download_table.columns().visible();
    for (var i = 0; i < visibility.length; i++) {
        if (!(visibility[i])) { media_download_child_table[rowData['rating_key']].column(i).visible(visibility[i]); }
    }
    media_download_table.on('column-visibility', function (e, settings, colIdx, visibility) {
        if (row.child.isShown()) {
            media_download_child_table[rowData['rating_key']].column(colIdx).visible(visibility);
        }
    });

    // Child table expand detailed downloads
    $('table[id^=media_download_child-' + rowData['rating_key'] + ']').on('click', '> tbody > tr > td.expand-media-download a', function () {
        var table_id = $(this).closest('table').data('id');
        var tr = $(this).closest('tr');
        var row = media_download_child_table[table_id].row(tr);
        var rowData = row.data();

        $(this).find('i.fa').toggleClass('fa-plus-circle').toggleClass('fa-minus-circle');

        if (row.child.isShown()) {
            $('div.slider', row.child()).slideUp(function () {
                row.child.hide();
                tr.removeClass('shown');
                delete media_download_child_table[rowData['rating_key']];
            });
        } else {
            tr.addClass('shown');
            row.child(childTableFormatMediaDownload(rowData)).show();
            createChildTableMediaDownload(row, rowData);
        }
    });
}
