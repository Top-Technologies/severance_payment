{
    'name': 'Employee Severance',
    'version': '1.0',
    'summary': 'Calculate employee severance payment based on years worked',
    'description': """
        This module calculates the severance payment for employees based on the number of years they have worked.
    """,
    'author': 'Tamrat',
    'depends': ['hr', 'hr_contract', 'hr_payroll'],
    'data': [
        'views/print_severance_payment.xml',
        'views/severance_payment_views.xml',
        'data/severance_payment_rules.xml',

        'security/ir.model.access.csv',

    ],
    'installable': True,
    'application': False,
}
