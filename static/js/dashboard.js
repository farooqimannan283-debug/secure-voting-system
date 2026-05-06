const pieChart = new Chart(
    document.getElementById('pieChart'),
{
    type:'doughnut',

    data:{
        labels:[
            'Candidate A',
            'Candidate B',
            'Candidate C',
            'Candidate D'
        ],

        datasets:[{
            data:[42,29,18,11],

            backgroundColor:[
                '#3b82f6',
                '#22c55e',
                '#facc15',
                '#a855f7'
            ]
        }]
    }
});

const barChart = new Chart(
    document.getElementById('barChart'),
{
    type:'bar',

    data:{
        labels:[
            'Candidate A',
            'Candidate B',
            'Candidate C',
            'Candidate D'
        ],

        datasets:[{
            label:'Votes',

            data:[
                4162,
                2922,
                1732,
                1026
            ],

            backgroundColor:[
                '#3b82f6',
                '#22c55e',
                '#facc15',
                '#a855f7'
            ]
        }]
    }
});

const lineChart = new Chart(
    document.getElementById('lineChart'),
{
    type:'line',

    data:{
        labels:[
            '11:30',
            '11:45',
            '12:00',
            '12:15',
            '12:30',
            '12:45'
        ],

        datasets:[
        {
            label:'Candidate A',
            data:[1,3,6,8,10,12],
            borderColor:'#3b82f6',
            tension:0.4
        },

        {
            label:'Candidate B',
            data:[1,2,4,6,8,9],
            borderColor:'#22c55e',
            tension:0.4
        }
        ]
    }
});