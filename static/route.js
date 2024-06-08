$(document).ready(function(){
    $('#doctor').change(function(){
        var doctorId = $(this).val();

        $.ajax({
            url: '/get_free_slots/' + doctorId,
            type: 'GET',
            success: function(response){
                $('#date').empty();
                response.free_slots.forEach(function(slot) {
                    $('#date').append(new Option(slot.date, slot.date));
                });

                $('#type_service').empty();
                response.services.forEach(function(service) {
                    $('#type_service').append(new Option(service.name, service.id));
                });

                $('#date').trigger('change');
            },
            error: function(xhr, status, error) {
                console.error('Ошибка при получении данных:', error);
            }
        });
    });

    $('#date').change(function(){
        var selectedDate = $(this).val();
        var doctorId = $('#doctor').val();

        $.ajax({
            url: '/get_free_slots/' + doctorId,
            type: 'GET',
            data: { date: selectedDate },
            success: function(response){
                $('#time').empty();
                var slots = response.free_slots.find(slot => slot.date === selectedDate);
                if (slots) {
                    slots.times.forEach(function(time) {
                        $('#time').append(new Option(time, time));
                    });
                } else {
                    console.error('Для выбранной даты нет доступных слотов.');
                }
            },
            error: function(xhr, status, error) {
                console.error('Ошибка при получении свободных слотов:', error);
            }
        });
    });

    $('form').submit(function(event) {
        var phone = $('#phone').val();
        var phonePattern = /^\+7\d{3}\d{3}\d{2}\d{2}$/;
        if (!phonePattern.test(phone)) {
            alert('Пожалуйста, введите номер телефона в формате +7XXXXXXXXXX');
            event.preventDefault();
        }
    });
    $('#doctor').trigger('change');
});