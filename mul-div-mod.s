	.section	__TEXT,__text,regular,pure_instructions
	.build_version macos, 12, 0	sdk_version 12, 3
	.globl	_main                           ## -- Begin function main
	.p2align	4, 0x90
_main:                                  ## @main
	.cfi_startproc
## %bb.0:
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset %rbp, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register %rbp
	subq	$48, %rsp
	movl	$0, -4(%rbp)
	leaq	L_.str(%rip), %rdi
	leaq	-16(%rbp), %rsi
	leaq	-24(%rbp), %rdx
	movb	$0, %al
	callq	_scanf
	movq	-16(%rbp), %rsi
	movq	-24(%rbp), %rax
	movq	%rax, -48(%rbp)                 ## 8-byte Spill
	movq	-16(%rbp), %rax
	cqto
	idivq	-24(%rbp)
	movq	-48(%rbp), %rdx                 ## 8-byte Reload
	movq	%rax, %rcx
	leaq	L_.str.1(%rip), %rdi
	movb	$0, %al
	callq	_printf
	movq	-16(%rbp), %rsi
	movq	-24(%rbp), %rax
	movq	%rax, -40(%rbp)                 ## 8-byte Spill
	movq	-16(%rbp), %rax
	cqto
	idivq	-24(%rbp)
	movq	%rdx, %rcx
	movq	-40(%rbp), %rdx                 ## 8-byte Reload
	leaq	L_.str.2(%rip), %rdi
	movb	$0, %al
	callq	_printf
	movq	-16(%rbp), %rsi
	movq	-24(%rbp), %rdx
	movq	-16(%rbp), %rcx
	imulq	-24(%rbp), %rcx
	leaq	L_.str.3(%rip), %rdi
	movb	$0, %al
	callq	_printf
	movq	-16(%rbp), %rsi
	movq	-24(%rbp), %rdx
	movq	-16(%rbp), %rax
	movq	-24(%rbp), %rcx
                                        ## kill: def $cl killed $rcx
	shlq	%cl, %rax
	movq	%rax, %rcx
	leaq	L_.str.4(%rip), %rdi
	movb	$0, %al
	callq	_printf
	movq	-16(%rbp), %rsi
	movq	-24(%rbp), %rdx
	movq	-16(%rbp), %rax
	movq	-24(%rbp), %rcx
                                        ## kill: def $cl killed $rcx
	sarq	%cl, %rax
	movq	%rax, %rcx
	leaq	L_.str.5(%rip), %rdi
	movb	$0, %al
	callq	_printf
	movq	-16(%rbp), %rsi
	movq	-24(%rbp), %rdx
	movq	-16(%rbp), %rcx
	andq	-24(%rbp), %rcx
	leaq	L_.str.6(%rip), %rdi
	movb	$0, %al
	callq	_printf
	movq	-16(%rbp), %rsi
	movq	-24(%rbp), %rdx
	movq	-16(%rbp), %rcx
	orq	-24(%rbp), %rcx
	leaq	L_.str.7(%rip), %rdi
	movb	$0, %al
	callq	_printf
	movq	-16(%rbp), %rsi
	movq	-24(%rbp), %rdx
	movq	-16(%rbp), %rcx
	xorq	-24(%rbp), %rcx
	leaq	L_.str.8(%rip), %rdi
	movb	$0, %al
	callq	_printf
	xorl	%eax, %eax
	addq	$48, %rsp
	popq	%rbp
	retq
	.cfi_endproc
                                        ## -- End function
	.section	__TEXT,__cstring,cstring_literals
L_.str:                                 ## @.str
	.asciz	"%ld %ld"

L_.str.1:                               ## @.str.1
	.asciz	"%ld / %ld = %ld\n"

L_.str.2:                               ## @.str.2
	.asciz	"%ld %% %ld = %ld\n"

L_.str.3:                               ## @.str.3
	.asciz	"%ld * %ld = %ld\n"

L_.str.4:                               ## @.str.4
	.asciz	"%ld << %ld = %ld\n"

L_.str.5:                               ## @.str.5
	.asciz	"%ld >> %ld = %ld\n"

L_.str.6:                               ## @.str.6
	.asciz	"%ld & %ld = %ld\n"

L_.str.7:                               ## @.str.7
	.asciz	"%ld | %ld = %ld\n"

L_.str.8:                               ## @.str.8
	.asciz	"%ld ^ %ld = %ld\n"

.subsections_via_symbols
