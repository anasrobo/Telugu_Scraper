class Bank{
float private amt = 0;
    void deposit (float d_amt){
        amt += d_amt;
    }
    void withdraw (float w_amt){
        if (w_amt > amt || w_amt <= 0) {
            System.out.println("Insufficient balance or invalid amount");
            return;
        }
        amt -= w_amt;
        System.out.println("Withdraw Successful: " + w_amt);
    }
    void balance (){
       i  System.out.println("Balance: " + amt);
    }
    public static void main(String[] args) {
        Bank myBank = new Bank();
        myBank.deposit(10000);
        myBank.withdraw(200);
        myBank.balance();
    }   
}