import yfinance as yf

class DCFModel:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.ticker_obj = yf.Ticker(ticker)
        self.info = self.ticker_obj.info
        self.cashflow = self.ticker_obj.cashflow
        self.shares_outstanding = self.info.get('sharesOutstanding', 1)
        
    def get_historical_fcf(self, years=5):
        """
        Returns a list of historical free cash flows for the last `years` years.
        """
        try:
            fcf = self.cashflow.loc['Total Cash From Operating Activities'] - self.cashflow.loc['Capital Expenditures']
            return fcf.head(years).tolist()
        except Exception:
            return []
        
    def estimate_growth_rate(self, historical_fcf):
        """
        Estimate FCF growth rate based on historical FCF values.
        """
        if not historical_fcf or len(historical_fcf) < 2:
            return 0.05  # fallback or industry/default
        start = historical_fcf[-1]
        end = historical_fcf[0]
        n = len(historical_fcf) - 1
        if start <= 0 or end <= 0:
            return 0.05
        return (end / start) ** (1 / n) - 1

    def get_discount_rate(self):
        """
        Use a default or computed discount rate (could be enhanced for WACC).
        """
        return 0.10  # 10% as typical example
    
    def calculate_terminal_value(self, last_fcf, growth_rate, discount_rate):
        return last_fcf * (1 + growth_rate) / (discount_rate - growth_rate)

    def compute_dcf_price(self, projection_years=5):
        """
        Calculates the intrinsic value per share using the DCF method.
        """
        fcf_list = self.get_historical_fcf(years=projection_years)
        if not fcf_list:
            return None
        avg_fcf = sum(fcf_list) / len(fcf_list)
        growth_rate = self.estimate_growth_rate(fcf_list)
        discount_rate = self.get_discount_rate()
        dcf_sum = 0

        for i in range(1, projection_years + 1):
            projected_fcf = avg_fcf * ((1 + growth_rate) ** i)
            dcf_sum += projected_fcf / ((1 + discount_rate) ** i)

        terminal_value = self.calculate_terminal_value(projected_fcf, growth_rate, discount_rate)
        dcf_sum += terminal_value / ((1 + discount_rate) ** projection_years)

        intrinsic_value = dcf_sum / self.shares_outstanding
        return intrinsic_value

# Example usage:
if __name__ == "__main__":
    ticker = 'AAPL'
    dcf = DCFModel(ticker)
    price = dcf.compute_dcf_price()
    print(f"DCF intrinsic value per share for {ticker}: {price}")
