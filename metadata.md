## 🧾 Table Schema: `bank_customer_data`

| Column Name             | Data Type     | Business Description                                                                 |
|-------------------------|---------------|--------------------------------------------------------------------------------------|
| `CustomerID`            | String        | Unique identifier assigned to each customer (e.g. "C001")                           |
| `Name`                  | String        | Full name of the customer                                                           |
| `Age`                   | Integer       | Age of the customer in years                                                        |
| `Gender`                | String        | Gender identity of the customer ("Male", "Female", "Non-Binary")                   |
| `Location`              | String        | Customer’s primary city of residence                                                |
| `AccountType`           | String        | Type of bank account held ("Checking" or "Savings")                                |
| `Balance`               | Float         | Current available balance in the account, in USD                                    |
| `AccountOpenDate`       | Date          | Date the customer opened the account                                                |
| `TxnCount_1M`           | Integer       | Number of transactions made in the last 1 month                                     |
| `TxnCount_3M`           | Integer       | Number of transactions made in the last 3 months                                    |
| `TxnCount_12M`          | Integer       | Number of transactions made in the last 12 months                                   |
| `AvgTxnAmt_1M`          | Float         | Average dollar amount per transaction over the last 1 month                         |
| `AvgTxnAmt_3M`          | Float         | Average dollar amount per transaction over the last 3 months                        |
| `AvgTxnAmt_12M`         | Float         | Average dollar amount per transaction over the last 12 months                       |
| `TotalDeposits_3M`      | Float         | Total value of deposits made in the last 3 months, in USD                           |
| `TotalWithdrawals_3M`   | Float         | Total value of withdrawals made in the last 3 months, in USD                        |