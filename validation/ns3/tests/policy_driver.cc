// policy_driver.cc - reads decision cases from stdin, prints sasp::Decide results.
// Input line:  mode sigmaPair n  (flow weight predT)*n   |   "root wa wb"
// Output line: reserve indices separated by ',' (or '-' if none) and reason; or u*.
#include "../src/sasp-policy.h"
#include <cstdio>
#include <iostream>
#include <sstream>
int main()
{
    std::string line;
    while (std::getline(std::cin, line))
    {
        std::istringstream in(line);
        std::string kind;
        in >> kind;
        if (kind == "root")
        {
            double a, b;
            in >> a >> b;
            std::printf("%.12g\n", sasp::ThresholdRoot(a, b));
            continue;
        }
        int mode, n;
        double sigma;
        in >> mode >> sigma >> n;
        std::vector<sasp::Candidate> c(n);
        for (auto& x : c)
        {
            in >> x.flow >> x.weight >> x.predT;
        }
        auto d = sasp::Decide(static_cast<sasp::Mode>(mode), c, sigma);
        if (d.reserve.empty())
        {
            std::printf("-");
        }
        for (std::size_t i = 0; i < d.reserve.size(); ++i)
        {
            std::printf("%s%d", i ? "," : "", d.reserve[i]);
        }
        std::printf(" %s\n", d.reason);
    }
}
