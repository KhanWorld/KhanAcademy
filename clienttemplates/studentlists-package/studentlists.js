var Util = {
    toDict: function(sequence, key_extractor) {
        var key_extractor_fn = null;
        if ((typeof key_extractor) == "string")
            key_extractor_fn = function(el) {return el[key_extractor];};
        else
            key_extractor_fn = key_extractor;

        var dict = {};
        $.each(sequence, function(i, item) {
            dict[key_extractor_fn(item)] = item;
        });
        return dict;
    }
};

var StudentLists = {

    Data: {
        students: null,
        students_by_id: null,
        students_by_email: null,
        student_lists: null,
        student_lists_by_id: null,
        coach_requests: null,

        init: function() {
            this.generateListIndices();
            this.generateStudentIndices();
        },

        isStudentInList: function(student_id, list_id) {
            var student = this.students_by_id[student_id];
            return $.grep(student.student_lists, function(list, i) {
                return list.key==list_id;
            }).length != 0;
        },

        addList: function(student_list) {
            this.student_lists.push(student_list);
            this.student_lists_by_id[student_list.key] = student_list;
        },

        removeList: function(list_id) {
            $.each(this.students, function(i, s) {
                StudentLists.Data.removeStudentFromList(s, list_id);
            });

            this.student_lists = $.grep(this.student_lists, function(list) {
                return list.key != list_id;
            });

            this.generateListIndices();
        },

        removeStudent: function(student) {
            var index = this.students.indexOf(student);
            if (index != -1)
                this.students.splice(index, 1);

            this.generateStudentIndices();
        },

        removeStudentFromList: function(student, list_id) {
            student.student_lists = $.grep(student.student_lists, function(list) {
                return list.key != list_id;
            });
        },

        addStudentToList: function(student, list_id) {
            student.student_lists.push(this.student_lists_by_id[list_id]);
        },

        generateListIndices: function() {
            this.student_lists_by_id = Util.toDict(StudentLists.Data.student_lists, 'key');
        },

        generateStudentIndices: function() {
            this.students_by_id = Util.toDict(StudentLists.Data.students, 'key');
            this.students_by_email = Util.toDict(StudentLists.Data.students, 'email');
        }
    },

    currentList: null,

    init: function() {
        StudentLists.Data.init();

        AddStudentTextBox.init();
        AddStudentToListTextBox.init();
        EditListsMenu.init();
        AddListTextBox.init();

        // change visible list
        $('.bullet').click(StudentLists.listClick);

        // inline delete student-list
        $('.student-row .delete-button').click(StudentLists.deleteStudentClick);

        // alerts
        $('.alert .close-button').click(function(event) {
            event.preventDefault();
            $(event.target).parents('.alert').fadeOut();
        });

        // show initial page
        // todo: remember this with a cookie!
        $('#student-list-allstudents a').click();
    },

    deleteStudentClick: function(event) {
        event.preventDefault();
        var jelRow = $(event.currentTarget).parents('.student-row');
        var student_id = jelRow.data('student_id');
        var student = StudentLists.Data.students_by_id[student_id];

        if (StudentLists.currentList == 'allstudents') {
            // this deletes the student-coach relationship: be sure
            var sure = confirm('Are you sure you want to stop coaching this student?');
            if (sure) {
                $.ajax({
                    type: 'GET',
                    url: '/unregisterstudent',
                    data: {'student_email': student.email}
                });

                // update data model
                StudentLists.Data.removeStudent(student);

                // update view
                $('.student-row[data-student_id='+student.key+']').fadeOut(
                    400,
                    function() { $(this).remove(); }
                );
                StudentLists.redrawListView();
            }
        }
        else if (StudentLists.currentList == 'requests') {
            var email = jelRow.data('email');

            $.ajax({
                type: 'GET',
                url: '/acceptcoach',
                data: {'accept': 0, 'student_email': email}
            });

            // update data model
            StudentLists.Data.coach_requests =
                $.grep(StudentLists.Data.coach_requests, function(request) {
                    return request != email;
                });

            // update UI
            jelRow.remove();
            StudentLists.redrawListView();
        }
        else {
            var list_id = StudentLists.currentList;
            EditListsMenu.removeStudentFromListAjax(student, list_id);
        }
    },

    listClick: function(event) {
        event.preventDefault();
        var jelSelectedList = $(event.currentTarget);

        var list_id = jelSelectedList.closest('li').data('list_id');
        if(list_id == StudentLists.currentList) {
            return;
        }
        StudentLists.currentList = list_id;

        $('.bullet-active').removeClass('bullet-active');
        jelSelectedList.addClass('bullet-active');

        StudentLists.redrawListView();
    },

    redrawListView: function() {
        // show or hide students depending on list membership
        var nstudents = 0;
        var title;
        var titleHref;
        var countstring = 'student';

        if(StudentLists.currentList == 'requests') {
            $('#actual-students').hide();
            $('#requested-students').show();
            nstudents = $('#requested-students .student-row').length;
            if(nstudents > 0) {
                $('#notaccepted-note').show();
            } else {
                $('#request-note').show();
            }
            $('#empty-class').hide();

            title = 'Requests';
            $('.students-header h2 a').removeAttr('href');
            $('#delete-list').hide();
            countstring = 'potential student';
        }
        else {
            $('#requested-students').hide();
            $('#actual-students').show();

            $('#notaccepted-note').hide();
            $('#request-note').hide();

            if(StudentLists.currentList=='allstudents') {
                var jelAll = $('#actual-students .student-row');
                jelAll.show();

                nstudents = jelAll.length;
                title = 'All students';
                titleHref = '/class_profile';
                $('#delete-list').hide();
                if(StudentLists.Data.students.length == 0) {
                    $('#empty-class').show();
                }
                else {
                    $('#empty-class').hide();
                }
            }
            else {
                $('#actual-students .student-row').each(function() {
                    var jel = $(this);
                    var student_id = jel.data('student_id');
                    if(StudentLists.Data.isStudentInList(student_id, StudentLists.currentList)) {
                        jel.show();
                        nstudents++;
                    }
                    else {
                        jel.hide();
                    }
                    $('#empty-class').hide();
                });

                var list = StudentLists.Data.student_lists_by_id[StudentLists.currentList];
                title = list.name;
                titleHref = '/class_profile?list_id=' + list.key;
                $('#delete-list').show();
            }
        }

        if (StudentLists.currentList == 'requests' || StudentLists.currentList == 'allstudents') {
            AddStudentTextBox.jElement.show();
            AddStudentToListTextBox.jElement.hide();
        }
        else {
            AddStudentTextBox.jElement.hide();
            AddStudentToListTextBox.jElement.show();
        }

        var nstudentsStr = nstudents.toString() + ' '
                                                + countstring
                                                + (nstudents==1 ? '' : 's');
        $('#nstudents').text(nstudentsStr);
        $('.students-header h2 a').text(title).attr('href', titleHref);
    }
};

var AddListTextBox = {
    jElement: null,
    jNewListElement: null,

    init: function() {
        this.jElement = $('#newlist-box')
            .keypress(function(event) {
                if (event.which == '13') { // enter
                    event.preventDefault();
                    AddListTextBox.createList(event);
                }
            })
            .keyup(function(event) {
                if (event.which == '27') { // escape
                    AddListTextBox.hide();
                }
            });

        $('#newlist-ok')
            .click(function(event) {
                AddListTextBox.createList(event);
            });

        $('#newlist-cancel')
            .click(function(event) {
                AddListTextBox.hide();
            });

        $('#newlist-button').click(function(event) {
            event.stopPropagation();
            event.preventDefault();
            $('#newlist-div').show();
            $('#newlist-button').hide();
            AddListTextBox.jElement.focus();
        });

        $('#newlist-div').hide();

        $('#delete-list').click(this.deleteList);
    },

    createList: function(event) {
        var listname = this.jElement.val();

        if (!listname) {
            this.hide();
            return;
        }

        this.jElement.attr('disabled', 'disabled');
        Throbber.show(this.jElement);
        $.ajax({
            type: 'POST',
            url: '/createstudentlist',
            data: {'list_name': listname},
            dataType: 'json',
            success: function(data, status, jqxhr) {
                var student_list = data;
                StudentLists.Data.addList(student_list);

                // add a new item to the sidebar
                var jel = $('<li data-list_id="'+student_list.key+'"><a href="students?list_id='+student_list.key+'" class="bullet">'+student_list.name+'</a></li>');
                $('#custom-lists').append(jel);
                jel.find('a').click(StudentLists.listClick);
            },
            complete: function(){
                Throbber.hide();
                AddListTextBox.hide();
            }
        });
    },

    hide: function() {
        AddListTextBox.jElement
            .val('')
            .removeAttr('disabled');
        $('#newlist-div').hide();
        $('#newlist-button').show().focus();
    },

    deleteList: function(event) {
        event.preventDefault();
        if (StudentLists.currentList != 'allstudents' &&
            StudentLists.currentList != 'requests') {
                $.ajax({
                    type: 'POST',
                    url: '/deletestudentlist',
                    data: {'list_id': StudentLists.currentList}
                });

                $('#custom-lists li[data-list_id='+StudentLists.currentList+']').remove();
                StudentLists.Data.removeList(StudentLists.currentList);
                $('#student-list-allstudents a').click();
        }
    }
};

var AddStudentTextBox = {
    jElement: null,

    init: function() {
        this.jElement = $('#request-student')
            .keypress(function(event) {
                if (event.which == '13') {
                    var email = AddStudentTextBox.jElement.val();
                    Throbber.show(AddStudentTextBox.jElement);
                    $.ajax({
                        type: 'POST',
                        url: '/requeststudent',
                        data: {'student_email': email},
                        success: function(data, status, jqxhr) {
                            // data model
                            StudentLists.Data.coach_requests.push(email);

                            // UI
                            AddStudentTextBox.jElement.val('');

                            $('#tmpl .student-row').clone()
                                .data('email', email)
                                .find('.student-name').text(email).end()
                                .hide().prependTo('#requested-students')
                                .find('.delete-button').click(StudentLists.deleteStudentClick).end()
                                .fadeIn();

                            $('#student-list-requests a').click();
                        },
                        error: function(jqxhr) {
                            $('#addstudent-error').slideDown();
                        },
                        complete: function() {
                            Throbber.hide();
                        }
                    });
                }
            })
            .placeholder();
    }
};

var AddStudentToListTextBox = {
    jElement: null,

    init: function() {
        this.jElement = $('#add-to-list')
            .keypress(function(event) {
                if (event.which == '13') { // enter
                    event.preventDefault();
                    AddStudentToListTextBox.addStudent(event);
                }
            })
            .placeholder()
            .autocomplete({
                source: AddStudentToListTextBox.generateSource(),
                select: function(event, selected) {
                    AddStudentToListTextBox.addStudent(event, selected);
                }
            });

        this.jElement.data("autocomplete").menu.select = function(e) {
            // jquery-ui.js's ui.autocomplete widget relies on an implementation of ui.menu
            // that is overridden by our jquery.ui.menu.js.  We need to trigger "selected"
            // here for this specific autocomplete box, not "select."
            this._trigger("selected", e, { item: this.active });
        };
    },

    generateSource: function() {
        return $.map(StudentLists.Data.students, function(student, i) {
            return { label: student.nickname + ' (' + student.email + ')',
                     value: student.email };
        });
    },

    updateSource: function() {
        this.jElement.data('autocomplete').options.source = this.generateSource();
        this.jElement.data('autocomplete')._initSource();
    },

    addStudent: function(event, selected) {
        var text;
        if (selected) {
            text = selected.item.value;
            event.preventDefault();
        }
        else {
            text = this.jElement.val();
        }

        var student = StudentLists.Data.students_by_email[text];
        var list_id = StudentLists.currentList;
        EditListsMenu.addStudentToListAjax(student, list_id);

        this.jElement.val('');
    }
};


var EditListsMenu = {
    init: function() {
        $('.lists-css-menu > ul > li').click(function(event){EditListsMenu.addChildrenToDropdown(event);});

        $('.lists-css-menu .list-option-newlist').click(function(event) {
            // if this is called synchronously, the css-menu doesn't disappear.
            setTimeout(function() {
                $('#newlist-button').click();
            }, 50);
        });
    },

    addChildrenToDropdown: function(event) {
        if(event.target != event.currentTarget) {
            // stopPropagation etc don't work on dynamically generated children.
            // http://api.jquery.com/event.stopPropagation/#comment-82290989
            return true;
        }
        var jelMenu = $(event.currentTarget);
        var jelUl = jelMenu.find('ul');
        if (jelUl.length == 0) {
            jelUl = $('<ul></ul>');
            jelMenu.append(jelUl);
        }
        jelUl.children('.list-option').remove();
        var jelNewList = jelUl.children('li');

        // add a line for each list
        $.each(StudentLists.Data.student_lists, function(i, studentList) {
            var jel = $('<li class="list-option"><label><input type="checkbox">' + studentList.name + '</label></li>');
            var jelInput = jel.find('input');

            // get student
            var student_id = jelMenu.closest('.student-row').data('student_id');
            if(StudentLists.Data.isStudentInList(student_id, studentList.key)) {
                jelInput.attr('checked', true);
            }

            jelNewList.before(jel);
            jelInput.click(EditListsMenu.itemClick)
                  .data('student-list', studentList);
        });

        // css menus will overlap the footer if they are at the bottom of page
        // fix by increasing the size of the .push element. Overshoot so we have
        // a bit more room to grow if they add more lists.
        var height = jelUl.height();
        if (height > $('.push').height()) {
            var overshoot = 30;
            $('.push').css('height', height + overshoot + 'px');
        }
    },

    itemClick: function(event) {
        var jelInput = $(event.currentTarget);
        var studentList = jelInput.data('student-list');
        var student_id = jelInput.closest('.student-row').data('student_id');
        var student = StudentLists.Data.students_by_id[student_id];
        if (jelInput.get(0).checked)
            EditListsMenu.addStudentToListAjax(student, studentList.key);
        else
            EditListsMenu.removeStudentFromListAjax(student, studentList.key);
    },

    addStudentToListAjax: function(student, list_id) {
        $.ajax({
            type: 'POST',
            url: '/addstudenttolist',
            data: {'student_email': student.email, 'list_id': list_id}
        });

        StudentLists.Data.addStudentToList(student, list_id);

        // show row on screen if visible
        if (StudentLists.currentList == list_id) {
            $('.student-row[data-student_id='+student.key+']').fadeIn();
        }
    },

    removeStudentFromListAjax: function(student, list_id) {
        $.ajax({
            type: 'POST',
            url: '/removestudentfromlist',
            data: {'student_email': student.email, 'list_id': list_id}
        });

        StudentLists.Data.removeStudentFromList(student, list_id);

        // hide row from screen if visible
        if (StudentLists.currentList == list_id) {
            $('.student-row[data-student_id='+student.key+']').fadeOut();
        }
    }
};
