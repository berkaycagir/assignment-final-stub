#include <stdio.h>

int main(void) {
	long i, j, k;
	scanf("%ld %ld", &i, &j);
	printf("%ld / %ld = %ld\n", i, j, i / j);
	printf("%ld %% %ld = %ld\n", i, j, i % j);
	printf("%ld * %ld = %ld\n", i, j, i * j);
	printf("%ld << %ld = %ld\n", i, j, i << j);
	printf("%ld >> %ld = %ld\n", i, j, i >> j);
	printf("%ld & %ld = %ld\n", i, j, i & j);
	printf("%ld | %ld = %ld\n", i, j, i | j);
	printf("%ld ^ %ld = %ld\n", i, j, i ^ j);
	return 0;
}
